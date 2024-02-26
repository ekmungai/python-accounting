import pytest
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from python_accounting.models import (
    LineItem,
    Entity,
    Account,
    Transaction,
    Tax,
)
from python_accounting.exceptions import NegativeValueError, HangingTransactionsError
from python_accounting.transactions import ClientInvoice


def test_line_item_entity(session, entity, currency):
    """Tests the relationship between a line item and its associated entity"""

    account = Account(
        name="test Line Item account",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)
    session.flush()

    line_item = LineItem(
        narration="Test line item",
        account_id=account.id,
        amount=10,
        entity_id=entity.id,
    )
    session.add(line_item)
    session.commit()

    line_item = session.get(LineItem, line_item.id)
    assert line_item.entity.name == "Test Entity"
    assert line_item.account.name == "Test Line Item Account"


def test_line_item_validation(session, entity, currency):
    """Tests the validation of line_item objects"""

    account = Account(
        name="test line_item account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)
    session.flush()

    line_item = LineItem(
        narration="Test line item",
        account_id=account.id,
        amount=-1,
        entity_id=entity.id,
    )
    session.add(line_item)
    with pytest.raises(NegativeValueError) as e:
        session.commit()
    assert str(e.value) == "LineItem amount cannot be negative."

    line_item.amount = 10
    line_item.quantity = -1
    session.add(line_item)

    with pytest.raises(NegativeValueError) as e:
        session.commit()
    assert str(e.value) == "LineItem quantity cannot be negative."


def test_line_item_isolation(session, entity, currency):
    """Tests the isolation of line_item objects by entity"""

    account = Account(
        name="test line_item account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)

    entity2 = Entity(name="Test Entity Two")
    session.add(entity2)
    session.flush()
    entity2 = session.get(Entity, entity2.id)

    session.add_all(
        [
            LineItem(
                narration="Test line item one",
                account_id=account.id,
                amount=10,
                entity_id=entity.id,
            ),
            LineItem(
                narration="Test line item two",
                account_id=account.id,
                amount=5,
                entity_id=entity2.id,
            ),
        ]
    )
    session.commit()

    line_itemes = session.scalars(select(LineItem)).all()

    assert len(line_itemes) == 1
    assert line_itemes[0].narration == "Test line item one"
    assert line_itemes[0].amount == 10
    assert line_itemes[0].entity.name == "Test Entity"

    line_item2 = session.get(LineItem, 2)
    assert line_item2 == None

    session.entity = entity2
    line_itemes = session.scalars(select(LineItem)).all()

    assert len(line_itemes) == 1
    assert line_itemes[0].narration == "Test line item two"
    assert line_itemes[0].amount == 5
    assert line_itemes[0].entity.name == "Test Entity Two"

    line_item1 = session.get(LineItem, 1)
    assert line_item1 == None


def test_line_item_recycling(session, entity, currency):
    """Tests the deleting, restoring and destroying functions of the line_item model"""

    account = Account(
        name="test line item account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)
    session.flush()

    line_item = LineItem(
        narration="Test line item one",
        account_id=account.id,
        amount=10,
        entity_id=entity.id,
    )
    session.add(line_item)
    session.flush()

    line_item_id = line_item.id

    session.delete(line_item)

    line_item = session.get(LineItem, line_item_id)
    assert line_item == None

    line_item = session.get(LineItem, line_item_id, include_deleted=True)
    assert line_item != None
    session.restore(line_item)

    line_item = session.get(LineItem, line_item_id)
    assert line_item != None

    session.destroy(line_item)

    line_item = session.get(LineItem, line_item_id)
    assert line_item == None

    line_item = session.get(LineItem, line_item_id, include_deleted=True)
    assert line_item != None
    session.restore(line_item)  # destroyed models canot be restored

    line_item = session.get(LineItem, line_item_id)
    assert line_item == None


def test_line_item_ledgers(session, entity, currency):
    """Tests the adding and removal of ledgers to line items"""
    account1 = Account(
        name="test transaction account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test line item account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add_all([account1, account2])
    session.flush()

    transaction = Transaction(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account1.id,
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        entity_id=entity.id,
    )
    session.add(transaction)

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account2.id,
        amount=10,
        entity_id=entity.id,
    )

    session.add(line_item1)
    session.flush()

    transaction.line_items.add(line_item1)
    session.add(transaction)

    transaction.post(session)

    with pytest.raises(ValueError) as e:
        line_item1.ledgers.remove(line_item1.ledgers[0])
    assert str(e.value) == "Line Item ledgers cannot be Removed manually."

    with pytest.raises(ValueError) as e:
        line_item1.ledgers.append(line_item1.ledgers[0])
    assert str(e.value) == "Line Item ledgers cannot be Added manually."

    with pytest.raises(HangingTransactionsError) as e:
        session.delete(line_item1)
    assert (
        str(e.value)
        == """The LineItem cannot be deleted because it has Transactions in
         the current reporting period."""
    )


def test_tax_inclusive_amount(session, entity, currency):
    """Tests that line item tax inclusive amounts are properly posted"""
    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test account two",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account3 = Account(
        name="test account three",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([account1, account2, account3])
    session.flush()

    transaction = ClientInvoice(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.commit()

    tax = Tax(
        name="Output Vat",
        code="OTPT",
        account_id=account3.id,
        rate=10,
        entity_id=entity.id,
    )
    session.add(tax)
    session.flush()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account2.id,
        amount=100,
        tax_inclusive=True,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    transaction.line_items.add(line_item1)
    session.add(transaction)
    session.flush()

    transaction.post(session)

    assert transaction.amount == 100
    assert account1.closing_balance(session) == 100
    assert account2.closing_balance(session) == Decimal("-90.9091")
    assert account3.closing_balance(session) == Decimal("-9.0909")
