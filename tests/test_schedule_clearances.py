from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from python_accounting.exceptions import OverclearanceError
from python_accounting.models import Account, Assignment, Balance, Transaction
from python_accounting.reports import AgingSchedule
from python_accounting.transactions import (
    ClientInvoice,
    ClientReceipt,
    SupplierBill,
    SupplierPayment,
)


def _accounts(session, entity, currency, payable=False):
    account = Account(
        name="Test supplier" if payable else "Test customer",
        account_type=(
            Account.AccountType.PAYABLE if payable else Account.AccountType.RECEIVABLE
        ),
        currency_id=currency.id,
        entity_id=entity.id,
    )
    line_account = Account(
        name="Test expense" if payable else "Test revenue",
        account_type=(
            Account.AccountType.OPERATING_EXPENSE
            if payable
            else Account.AccountType.OPERATING_REVENUE
        ),
        currency_id=currency.id,
        entity_id=entity.id,
    )
    bank = Account(
        name="Test bank",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([account, line_account, bank])
    session.flush()
    return account, line_account, bank


def _assign(session, subject, payment, date, amount):
    assignment = Assignment(
        assignment_date=date,
        transaction_id=payment.id,
        assigned_id=subject.id,
        assigned_type=subject.__class__.__name__,
        entity_id=subject.entity_id,
        amount=Decimal(amount),
    )
    session.add(assignment)
    session.commit()


def _assert_schedule(session, account, subject, cutoff, cleared, bracket, start=None):
    statement = account.statement(session, start, cutoff, True)
    outstanding = 100 - cleared
    assert statement["total_amount"] == (100 if outstanding else 0)
    assert statement["cleared_amount"] == (cleared if outstanding else 0)
    assert statement["uncleared_amount"] == outstanding
    assert statement["transactions"] == ([subject] if outstanding else [])
    if outstanding:
        assert subject.cleared_amount == cleared
        assert subject.uncleared_amount == outstanding

    aging = AgingSchedule(session, account.account_type, cutoff)
    expected = {key: 0 for key in AgingSchedule.brackets}
    expected[bracket] = outstanding
    assert aging.balances == expected
    assert aging.accounts == ([account] if outstanding else [])
    if outstanding:
        assert account.balances == expected


def _statement_values(session, account, cutoff):
    statement = account.statement(session, end_date=cutoff)
    return (
        statement["opening_balance"],
        statement["closing_balance"],
        [(row.id, row.debit, row.credit, row.balance) for row in statement["transactions"]],
    )


@pytest.mark.parametrize(
    "payable,opening",
    [(False, False), (True, False), (False, True), (True, True)],
    ids=["invoice", "bill", "receivable-opening", "payable-opening"],
)
def test_historical_partial_and_full_clearance(
    session, entity, currency, post_document, payable, opening
):
    """Later assignments do not change an earlier schedule or ageing report."""
    year = datetime.now().year
    cutoff = datetime(year, 1, 31)
    payment_date = datetime(year, 2, 15)
    account, line_account, bank = _accounts(session, entity, currency, payable)
    if opening:
        subject = Balance(
            transaction_date=datetime(year - 1, 12, 15),
            transaction_type=(
                Transaction.TransactionType.SUPPLIER_BILL
                if payable
                else Transaction.TransactionType.CLIENT_INVOICE
            ),
            amount=Decimal("100"),
            balance_type=(
                Balance.BalanceType.CREDIT if payable else Balance.BalanceType.DEBIT
            ),
            account_id=account.id,
            entity_id=entity.id,
        )
        session.add(subject)
        session.flush()
    else:
        subject = post_document(
            SupplierBill if payable else ClientInvoice,
            account,
            line_account,
            datetime(year, 1, 15),
            "100",
        )

    bracket = "31 - 90 days" if opening else "current"
    before = _statement_values(session, account, cutoff)
    _assert_schedule(session, account, subject, cutoff, 0, bracket)
    assert subject.cleared(session) == 0

    for amount, lifetime in [("40", 40), ("60", 100)]:
        payment = post_document(
            SupplierPayment if payable else ClientReceipt,
            account,
            bank,
            payment_date,
            amount,
        )
        _assign(session, subject, payment, payment_date, amount)
        assert subject.cleared(session) == lifetime
        _assert_schedule(session, account, subject, cutoff, 0, bracket)
        _assert_schedule(
            session,
            account,
            subject,
            datetime(year, 2, 14),
            0,
            "31 - 90 days" if opening else "current",
        )
        for day in (15, 28):
            _assert_schedule(
                session, account, subject, datetime(year, 2, day), lifetime, "31 - 90 days"
            )
        assert account.closing_balance(session, cutoff) == (-100 if payable else 100)
        assert _statement_values(session, account, cutoff) == before

    # Read the earlier date again after full clearance at a later date.
    _assert_schedule(session, account, subject, cutoff, 0, bracket)
    assert subject.cleared(session) == 100


def test_clearance_cutoff_boundaries(
    session, entity, currency, post_document, fixed_today
):
    """Reports include the whole cutoff day; direct clearance queries keep the timestamp."""
    year = fixed_today.year
    account, revenue, bank = _accounts(session, entity, currency)
    invoice = post_document(
        ClientInvoice, account, revenue, datetime(year, 1, 15), "100"
    )
    end_of_day = datetime(year, 1, 31, 23, 59, 59, 999999)
    next_day = datetime(year, 2, 1)
    for date, amount in [
        (datetime(year, 1, 30), "20"),
        (end_of_day, "30"),
        (next_day, "50"),
    ]:
        payment = post_document(ClientReceipt, account, bank, date, amount)
        _assign(session, invoice, payment, date, amount)

    _assert_schedule(
        session, account, invoice, datetime(year, 1, 31), 50, "current",
        start=datetime(year, 1, 31),
    )
    _assert_schedule(session, account, invoice, None, 50, "current")
    assert invoice.cleared(session, end_date=end_of_day) == 50
    assert invoice.cleared(session, end_date=end_of_day - timedelta(microseconds=1)) == 20
    assert invoice.cleared(session, end_date=next_day) == 100
    assert invoice.cleared(session) == 100
    assert invoice.cleared(session, end_date=None) == 100
    _assert_schedule(session, account, invoice, next_day, 100, "current")


@pytest.mark.parametrize(
    "payment_month,assignment_month,outstanding",
    [(1, 2, 100), (2, 1, 0)],
)
def test_assignment_date_controls_clearance(
    session, entity, currency, post_document, payment_month, assignment_month, outstanding
):
    """Allocation dates remain independent of the payment's ledger date."""
    year = datetime.now().year
    account, revenue, bank = _accounts(session, entity, currency)
    invoice = post_document(
        ClientInvoice, account, revenue, datetime(year, 1, 15), "100"
    )
    payment = post_document(
        ClientReceipt, account, bank, datetime(year, payment_month, 20), "100"
    )
    _assign(session, invoice, payment, datetime(year, assignment_month, 20), "100")
    _assert_schedule(
        session, account, invoice, datetime(year, 1, 31), 100 - outstanding, "current"
    )


def test_future_clearance_still_prevents_overclearance(
    session, entity, currency, post_document
):
    """Reporting cutoffs do not relax lifetime allocation validation."""
    year = datetime.now().year
    account, revenue, bank = _accounts(session, entity, currency)
    invoice = post_document(
        ClientInvoice, account, revenue, datetime(year, 1, 15), "100"
    )
    future_date = datetime(year, 2, 15)
    payment = post_document(ClientReceipt, account, bank, future_date, "100")
    _assign(session, invoice, payment, future_date, "100")
    extra_payment = post_document(
        ClientReceipt, account, bank, datetime(year, 1, 31), "1"
    )
    with pytest.raises(OverclearanceError):
        _assign(session, invoice, extra_payment, datetime(year, 1, 31), "1")


def test_bulk_assignment_keeps_lifetime_capacity(
    session, entity, currency, post_document, fixed_today
):
    """Bulk allocation skips full reservations and uses each remaining lifetime capacity."""
    year = fixed_today.year
    account, revenue, bank = _accounts(session, entity, currency)
    first = post_document(ClientInvoice, account, revenue, datetime(year, 1, 5), "100")
    second = post_document(ClientInvoice, account, revenue, datetime(year, 1, 10), "100")
    third = post_document(ClientInvoice, account, revenue, datetime(year, 1, 15), "40")
    future_date = datetime(year, 2, 15)
    for subject, amount in [(first, "100"), (second, "40")]:
        payment = post_document(ClientReceipt, account, bank, future_date, amount)
        _assign(session, subject, payment, future_date, amount)

    payment = post_document(ClientReceipt, account, bank, fixed_today, "100")
    payment.bulk_assign(session)
    assert sorted((a.assigned_id, a.amount) for a in payment.assignments(session)) == [
        (second.id, 60),
        (third.id, 40),
    ]
    assert first.cleared(session) == 100
    assert second.cleared(session) == 100
    assert third.cleared(session) == 40
    assert payment.balance(session) == 0
