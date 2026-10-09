from datetime import datetime
from decimal import Decimal, localcontext

import pytest
from sqlalchemy import select

from python_accounting.models import Account, Balance, Ledger, LineItem, Tax
from python_accounting.transactions import CashPurchase, CashSale


@pytest.fixture
def tax_document(session, entity, currency):
    """Create persisted tax documents using the existing accounting session."""
    accounts = [
        Account(
            name=name,
            account_type=kind,
            currency_id=currency.id,
            entity_id=entity.id,
        )
        for name, kind in [
            ("Bank", Account.AccountType.BANK),
            ("Sales", Account.AccountType.OPERATING_REVENUE),
            ("Purchases", Account.AccountType.OPERATING_EXPENSE),
            ("Tax", Account.AccountType.CONTROL),
        ]
    ]
    session.add_all(accounts)
    session.flush()
    bank, sales, purchases, control = accounts

    def create(document_type, lines):
        document = document_type(
            narration="Tax summary test",
            transaction_date=datetime.now(),
            account_id=bank.id,
            entity_id=entity.id,
        )
        session.add(document)
        session.flush()
        taxes = {}
        for amount, quantity, inclusive, code, rate in lines:
            if code is not None and code not in taxes:
                tax = Tax(
                    name=code,
                    code=code,
                    rate=Decimal(rate),
                    account_id=control.id,
                    entity_id=entity.id,
                )
                session.add(tax)
                session.flush()
                taxes[code] = tax
            line = LineItem(
                narration="Tax summary line",
                account_id=(purchases if document_type is CashPurchase else sales).id,
                amount=Decimal(amount),
                quantity=Decimal(quantity),
                tax_inclusive=inclusive,
                tax_id=taxes[code].id if code is not None else None,
                entity_id=entity.id,
            )
            session.add(line)
            session.flush()
            document.line_items.add(line)
        session.flush()
        return document, control

    return create


@pytest.mark.parametrize("document_type", [CashSale, CashPurchase])
@pytest.mark.parametrize(
    "amount,quantity,inclusive,rate,expected_tax,expected_amount",
    [
        ("40", "2.5", False, "10", "10", "110"),
        ("44", "2.5", True, "10", "10", "110"),
        ("18", "2", True, "12.5", "4", "36"),
        ("100.025", "2.5", True, "0.025", "0.0625", "250.0625"),
        ("0", "2.5", True, "10", "0", "0"),
    ],
)
def test_transaction_tax_matches_simple_posting(
    session, tax_document, document_type, amount, quantity, inclusive, rate,
    expected_tax, expected_amount,
):
    document, control = tax_document(
        document_type, [(amount, quantity, inclusive, "TAX", rate)]
    )
    expected = {
        "total": Decimal(expected_tax),
        "taxes": {
            "TAX": {
                "name": "TAX",
                "rate": f"{round(Decimal(rate), 2)}%",
                "amount": Decimal(expected_tax),
            }
        },
    }
    assert document.tax == expected
    assert document.amount == Decimal(expected_amount)
    assert not session.dirty
    document.post(session)
    records = session.scalars(
        select(Ledger).where(Ledger.transaction_id == document.id)
    ).all()
    before = [(row.id, row.amount, row.hash) for row in records]
    assert len(records) == 4
    assert sum(
        row.amount for row in records if row.post_account_id == control.id
    ) == Decimal(expected_tax)
    assert sum(row.amount for row in records if row.entry_type == Balance.BalanceType.DEBIT) == sum(
        row.amount for row in records if row.entry_type == Balance.BalanceType.CREDIT
    )
    for _ in range(2):
        assert document.tax == expected
    assert not session.dirty
    assert [(row.id, row.amount, row.hash) for row in records] == before
    assert document.is_secure(session)


def test_transaction_tax_aggregates_mixed_lines(tax_document, session):
    document, control = tax_document(
        CashSale,
        [
            ("44", "2.5", True, "GST", "10"),
            ("40", "2.5", False, "GST", "10"),
            ("18", "2", True, "OTHER", "12.5"),
            ("8", "0.5", False, "OTHER", "12.5"),
            ("200", "1", True, None, None),
        ],
    )
    expected = {
        "total": Decimal("24.5"),
        "taxes": {
            "GST": {"name": "GST", "rate": "10.00%", "amount": Decimal("20")},
            "OTHER": {"name": "OTHER", "rate": "12.50%", "amount": Decimal("4.5")},
        },
    }
    assert document.tax == expected
    assert document.amount == Decimal("460.5")
    document.post(session)
    assert document.tax == expected
    assert control.closing_balance(session) == Decimal("-24.5")


@pytest.mark.parametrize("lines", [[], [("100", "2.5", True, None, None)]])
def test_transaction_tax_without_taxes(tax_document, lines):
    document, _ = tax_document(CashSale, lines)
    assert document.tax == {"total": 0, "taxes": {}}
    assert type(document.tax["total"]) is int


def test_transaction_tax_retains_unrounded_precision(tax_document):
    document, _ = tax_document(CashSale, [("100", "1", True, "GST", "10")])
    with localcontext() as context:
        context.prec = 28
        expected = Decimal("9.09090909090909090909090909")
        assert document.tax["total"] == expected
        assert document.tax["taxes"]["GST"]["amount"] == expected


def test_transaction_tax_preserves_exclusive_decimal_order(tax_document):
    document, _ = tax_document(CashSale, [("11.11", "2.125", False, "TAX", "7.25")])
    with localcontext() as context:
        context.prec = 6
        assert document.tax["total"] == Decimal("1.71163")


def test_transaction_tax_with_flushed_integer_rate(session, tax_document):
    document, _ = tax_document(CashSale, [("110", "1", True, "TAX", "10")])
    tax = next(iter(document.line_items)).tax
    tax.rate = 10
    session.flush()
    assert type(tax.rate) is int
    assert document.tax["total"] == Decimal("10")
    assert isinstance(document.tax["total"], Decimal)
    assert not session.dirty
