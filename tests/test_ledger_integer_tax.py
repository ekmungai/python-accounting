from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from python_accounting.models import Account, Balance, Ledger, LineItem, Tax
from python_accounting.transactions import CashPurchase, CashSale, ClientInvoice, SupplierBill


@pytest.fixture
def inclusive_document(session, entity, currency):
    """Keep the new Tax alive so a lazy reload cannot mask its input rate type."""

    def create(document_type, rate, amount="110", quantity="2.5"):
        main_type = {
            CashSale: Account.AccountType.BANK,
            CashPurchase: Account.AccountType.BANK,
            ClientInvoice: Account.AccountType.RECEIVABLE,
            SupplierBill: Account.AccountType.PAYABLE,
        }[document_type]
        selling = document_type in (CashSale, ClientInvoice)
        accounts = [
            Account(name=name, account_type=kind, currency_id=currency.id, entity_id=entity.id)
            for name, kind in [
                ("Main", main_type),
                ("Trade", Account.AccountType.OPERATING_REVENUE if selling else Account.AccountType.OPERATING_EXPENSE),
                ("Tax", Account.AccountType.CONTROL),
            ]
        ]
        session.add_all(accounts)
        session.flush()
        main, trade, control = accounts
        tax = Tax(name="Tax", code="TAX", rate=rate, account_id=control.id, entity_id=entity.id)
        session.add(tax)
        session.flush()
        document = document_type(
            narration="Inclusive posting test", transaction_date=datetime.now(),
            account_id=main.id, entity_id=entity.id,
        )
        session.add(document)
        session.flush()
        line = LineItem(
            narration="Inclusive line", account_id=trade.id, amount=Decimal(amount),
            quantity=Decimal(quantity), tax_inclusive=True, tax_id=tax.id, entity_id=entity.id,
        )
        session.add(line)
        session.flush()
        document.line_items.add(line)
        session.flush()
        return document, main, trade, control, tax

    return create


@pytest.mark.parametrize("document_type", [CashSale, CashPurchase, ClientInvoice, SupplierBill])
@pytest.mark.parametrize("rate", [10, Decimal("10")], ids=["integer", "decimal"])
def test_inclusive_posting_with_unexpired_rate(session, inclusive_document, document_type, rate):
    document, main, trade, control, tax = inclusive_document(document_type, rate)
    document.post(session)
    document_id = document.id
    session.expire_all()
    records = session.scalars(select(Ledger).where(Ledger.transaction_id == document_id)).all()
    selling = document_type in (CashSale, ClientInvoice)
    main_entry = Balance.BalanceType.DEBIT if selling else Balance.BalanceType.CREDIT
    trade_entry = Balance.BalanceType.CREDIT if selling else Balance.BalanceType.DEBIT
    assert len(records) == 4
    assert {row.tax_id for row in records} == {tax.id, None}
    assert {
        (row.post_account_id, row.folio_account_id, row.entry_type, row.amount)
        for row in records
    } == {
        (main.id, trade.id, main_entry, Decimal("275.0000")),
        (trade.id, main.id, trade_entry, Decimal("275.0000")),
        (trade.id, control.id, main_entry, Decimal("25.0000")),
        (control.id, trade.id, trade_entry, Decimal("25.0000")),
    }
    assert sum(row.amount for row in records if row.entry_type == Balance.BalanceType.DEBIT) == Decimal("300.0000")
    assert sum(row.amount for row in records if row.entry_type == Balance.BalanceType.CREDIT) == Decimal("300.0000")
    sign = Decimal("1") if selling else Decimal("-1")
    assert main.closing_balance(session) == sign * Decimal("275.0000")
    assert trade.closing_balance(session) == -sign * Decimal("250.0000")
    assert control.closing_balance(session) == -sign * Decimal("25.0000")
    assert all(row.amount.as_tuple().exponent == -4 for row in records)
    assert document.is_secure(session)


@pytest.mark.parametrize("rate", [10, Decimal("10")], ids=["integer", "decimal"])
def test_inclusive_posting_rounds_and_hashes_reloaded_amounts(session, inclusive_document, rate):
    document, main, trade, control, tax = inclusive_document(CashSale, rate, amount="100", quantity="1")
    document.post(session)
    document_id = document.id
    session.expire_all()
    records = session.scalars(select(Ledger).where(Ledger.transaction_id == document_id)).all()
    assert len(records) == 4
    assert {row.tax_id for row in records} == {tax.id, None}
    assert sorted(row.amount for row in records) == [
        Decimal("9.0909"), Decimal("9.0909"), Decimal("100.0000"), Decimal("100.0000"),
    ]
    assert sum(row.amount for row in records if row.entry_type == Balance.BalanceType.DEBIT) == Decimal("109.0909")
    assert sum(row.amount for row in records if row.entry_type == Balance.BalanceType.CREDIT) == Decimal("109.0909")
    assert main.closing_balance(session) == Decimal("100.0000")
    assert trade.closing_balance(session) == Decimal("-90.9091")
    assert control.closing_balance(session) == Decimal("-9.0909")
    assert all(row.amount.as_tuple().exponent == -4 for row in records)
    assert document.is_secure(session)
