from datetime import datetime
from decimal import Decimal

import pytest

from python_accounting.models import Account, Assignment, Ledger, LineItem
from python_accounting.transactions import ClientInvoice, ClientReceipt


def _post(session, document_type, account, line_account, date, amount):
    document = document_type(
        narration="Test document",
        transaction_date=date,
        account_id=account.id,
        entity_id=account.entity_id,
    )
    session.add(document)
    session.flush()
    line = LineItem(
        narration="Test line",
        account_id=line_account.id,
        amount=Decimal(amount),
        entity_id=account.entity_id,
    )
    session.add(line)
    session.flush()
    document.line_items.add(line)
    session.flush()
    document.post(session)
    return document


@pytest.fixture
def allocation_day(monkeypatch):
    year = datetime.now().year

    class AllocationDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(year, 1, 31, 12, tzinfo=tz)

        @classmethod
        def today(cls):
            return cls.now()

    monkeypatch.setattr("python_accounting.utils.dates.datetime", AllocationDateTime)
    monkeypatch.setattr("python_accounting.mixins.assigning.datetime", AllocationDateTime)
    return AllocationDateTime.today()


@pytest.fixture
def invoices(session, entity, currency, allocation_day):
    account = Account(
        name="Test customer",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    other_account = Account(
        name="Other customer",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    revenue = Account(
        name="Test revenue",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    bank = Account(
        name="Test bank",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([account, other_account, revenue, bank])
    session.flush()
    # Create the documents out of date order to distinguish FIFO from insertion order.
    documents = {
        day: _post(
            session, ClientInvoice, account, revenue,
            datetime(allocation_day.year, 1, day), "100",
        )
        for day in (6, 7, 5)
    }
    other_invoice = _post(
        session, ClientInvoice, other_account, revenue,
        datetime(allocation_day.year, 1, 2), "100",
    )
    return account, bank, [documents[day] for day in (5, 6, 7)], other_invoice


def _assignments(payment, session):
    return sorted(payment.assignments(session), key=lambda assignment: assignment.id)


def _ledger_values(session):
    return [
        (row.id, row.transaction_id, row.amount, row.hash)
        for row in session.query(Ledger).order_by(Ledger.id).all()
    ]


@pytest.mark.parametrize(
    "amount,expected",
    [
        ("50", ["50"]),
        ("100", ["100"]),
        ("150", ["100", "50"]),
        ("200", ["100", "100"]),
        ("300", ["100", "100", "100"]),
        ("350", ["100", "100", "100"]),
        ("150.0001", ["100", "50.0001"]),
    ],
)
def test_bulk_assignment_stops_at_available_funds(
    session, invoices, allocation_day, amount, expected
):
    """Bulk allocation spends only available funds and leaves the ledger unchanged."""
    account, bank, documents, other_invoice = invoices
    payment = _post(session, ClientReceipt, account, bank, allocation_day, amount)
    ledger_before = _ledger_values(session)
    balance_before = payment.balance(session)

    assert payment.bulk_assign(session) is None
    assignments = _assignments(payment, session)
    expected_amounts = [Decimal(value) for value in expected]
    assert [(a.assigned_id, a.amount) for a in assignments] == [
        (document.id, value)
        for document, value in zip(documents, expected_amounts)
    ]
    assert all(a.amount > 0 for a in assignments)
    assert all(a.transaction_id == payment.id for a in assignments)
    assert all(a.entity_id == account.entity_id for a in assignments)
    assert all(a.assigned_type == ClientInvoice.__name__ for a in assignments)
    assert payment.balance(session) == balance_before - sum(expected_amounts)
    assert payment.balance(session) >= 0
    for document, cleared in zip(documents, expected_amounts + [0] * (3 - len(expected))):
        assert document.cleared(session) == cleared
        assert document.cleared(session) <= document.amount
    assert other_invoice.cleared(session) == 0
    assert _ledger_values(session) == ledger_before


def _reserved_payment(session, invoices, allocation_day, amount):
    account, bank, documents, _ = invoices
    payment = _post(session, ClientReceipt, account, bank, allocation_day, amount)
    assignment = Assignment(
        assignment_date=datetime(allocation_day.year, 2, 15),
        transaction_id=payment.id,
        assigned_id=documents[0].id,
        assigned_type=ClientInvoice.__name__,
        entity_id=account.entity_id,
        amount=Decimal("100"),
    )
    session.add(assignment)
    session.flush()
    return payment


@pytest.mark.parametrize("amount,expected_new", [("100", []), ("150", ["50"])])
def test_bulk_assignment_respects_lifetime_source_capacity(
    session, invoices, allocation_day, amount, expected_new
):
    """Existing future allocations consume capacity before bulk allocation starts."""
    payment = _reserved_payment(session, invoices, allocation_day, amount)
    documents = invoices[2]
    before = [(a.id, a.assigned_id, a.amount) for a in _assignments(payment, session)]
    balance_before = payment.balance(session)
    assert balance_before == Decimal(amount) - 100

    assert payment.bulk_assign(session) is None
    assignments = _assignments(payment, session)
    assert [(a.id, a.assigned_id, a.amount) for a in assignments[:1]] == before
    assert [(a.assigned_id, a.amount) for a in assignments[1:]] == [
        (documents[1].id, Decimal(value)) for value in expected_new
    ]
    assert all(a.amount > 0 for a in assignments)
    assert payment.balance(session) == 0
    assert documents[0].cleared(session) == 100
    assert documents[1].cleared(session) == sum(Decimal(value) for value in expected_new)
    assert documents[2].cleared(session) == 0

    snapshot = [(a.id, a.assigned_id, a.amount) for a in assignments]
    assert payment.bulk_assign(session) is None
    assert [(a.id, a.assigned_id, a.amount) for a in _assignments(payment, session)] == snapshot


def test_exhausted_source_still_evaluates_schedule(
    session, invoices, allocation_day, monkeypatch
):
    """An exhausted source still reaches the account's schedule validation boundary."""
    payment = _reserved_payment(session, invoices, allocation_day, "100")
    original_statement = Account.statement
    calls = []

    def statement(account, *args, **kwargs):
        calls.append(account.id)
        return original_statement(account, *args, **kwargs)

    monkeypatch.setattr(Account, "statement", statement)
    assert payment.bulk_assign(session) is None
    assert calls == [invoices[0].id]
    assert len(payment.assignments(session)) == 1


@pytest.mark.parametrize("amount,expected", [("50", ["50"]), ("70", ["60", "10"])])
def test_exhaustion_preserves_future_target_reservations(
    session, invoices, allocation_day, amount, expected
):
    """Source exhaustion and historical reports both retain lifetime target capacity."""
    account, bank, documents, _ = invoices
    revenue = session.get(Account, next(iter(documents[0].line_items)).account_id)
    documents.append(_post(
        session, ClientInvoice, account, revenue,
        datetime(allocation_day.year, 1, 8), "100",
    ))
    future_date = datetime(allocation_day.year, 2, 15)
    for document, reserved in zip(documents, ["100", "40"]):
        reservation = _post(session, ClientReceipt, account, bank, future_date, reserved)
        session.add(Assignment(
            assignment_date=future_date,
            transaction_id=reservation.id,
            assigned_id=document.id,
            assigned_type=ClientInvoice.__name__,
            entity_id=account.entity_id,
            amount=Decimal(reserved),
        ))
        session.flush()
        assert document.cleared(session, end_date=allocation_day) == 0

    payment = _post(session, ClientReceipt, account, bank, allocation_day, amount)
    ledger_before = _ledger_values(session)
    assert payment.bulk_assign(session) is None
    assignments = _assignments(payment, session)
    expected_amounts = [Decimal(value) for value in expected]
    assert [(a.assigned_id, a.amount) for a in assignments] == [
        (document.id, value)
        for document, value in zip(documents[1:], expected_amounts)
    ]
    assert all(a.amount > 0 for a in assignments)
    assert payment.balance(session) == 0
    assert sum(a.amount for a in assignments) == Decimal(amount)
    assert [document.cleared(session) for document in documents] == [
        100, 40 + expected_amounts[0],
        expected_amounts[1] if len(expected_amounts) > 1 else 0, 0,
    ]
    assert _ledger_values(session) == ledger_before
