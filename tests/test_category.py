import pytest
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from python_accounting.models import (
    Account,
    Category,
    Entity,
    Balance,
    Transaction,
    LineItem,
)
from python_accounting.transactions import ClientInvoice
from python_accounting.exceptions import InvalidAccountTypeError


def test_category_entity(session, entity):
    """Tests the relationship between a category and its associated entity"""
    category = Category(
        name="Test Category",
        category_account_type=Account.AccountType.BANK,
        entity_id=entity.id,
    )
    session.add(category)
    session.commit()

    category = session.get(Category, category.id)
    assert category.entity.name == "Test Entity"


def test_category_validation(session, entity):
    """Tests the validation of category objects"""
    with pytest.raises(InvalidAccountTypeError) as e:
        session.add(
            Category(
                name="Test Category",
                category_account_type="Accont Type",
                entity_id=entity.id,
            )
        )
    assert (
        str(e.value)
        == "category_account_type must be one of: Non Current Asset, Contra Asset, Inventory, Bank, Current Asset, Receivable, Non Current Liability, Control, Current Liability, Payable, Reconciliation, Equity, Operating Revenue, Operating Expense, Non Operating Revenue, Direct Expense, Overhead Expense, Other Expense."
    )


def test_category_isolation(session, entity):
    """Tests the isolation of category objects by entity"""

    entity2 = Entity(name="Test Entity Two")
    session.add(entity2)
    session.flush()
    entity2 = session.get(Entity, entity2.id)

    session.add_all(
        [
            Category(
                name="Test Category One",
                category_account_type=Account.AccountType.BANK,
                entity_id=entity.id,
            ),
            Category(
                name="Test Category Two",
                category_account_type=Account.AccountType.RECEIVABLE,
                entity_id=entity2.id,
            ),
        ]
    )
    session.commit()

    categories = session.scalars(select(Category)).all()

    assert len(categories) == 1
    assert categories[0].name == "Test Category One"
    assert categories[0].category_account_type == Account.AccountType.BANK
    assert categories[0].entity.name == "Test Entity"

    category2 = session.get(Category, 2)
    assert category2 == None

    session.entity = entity2
    categories = session.scalars(select(Category)).all()

    assert len(categories) == 1
    assert categories[0].name == "Test Category Two"
    assert categories[0].category_account_type == Account.AccountType.RECEIVABLE
    assert categories[0].entity.name == "Test Entity Two"

    category1 = session.get(Category, 1)
    assert category1 == None


def test_category_recycling(session, entity):
    """Tests the deleting, restoring and destroying functions of the category model"""

    category = Category(
        name="Test Category One",
        category_account_type=Account.AccountType.BANK,
        entity_id=entity.id,
    )
    session.add(category)
    session.flush()

    category_id = category.id

    session.delete(category)

    category = session.get(Category, category_id)
    assert category == None

    category = session.get(Category, category_id, include_deleted=True)
    assert category != None
    session.restore(category)

    category = session.get(Category, category_id)
    assert category != None

    session.destroy(category)

    category = session.get(Category, category_id)
    assert category == None

    category = session.get(Category, category_id, include_deleted=True)
    assert category != None
    session.restore(category)  # destroyed models canot be restored

    category = session.get(Category, category_id)
    assert category == None


def test_account_balances(session, entity, currency):
    """Tests the aggregation of account balances by category"""
    revenue_category = Category(
        name="Revenue Category",
        category_account_type=Account.AccountType.OPERATING_REVENUE,
        entity_id=entity.id,
    )
    client_category = Category(
        name="Client Category",
        category_account_type=Account.AccountType.RECEIVABLE,
        entity_id=entity.id,
    )
    session.add_all([revenue_category, client_category])
    session.commit()

    revenue = Account(
        name="revenue account",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        category_id=revenue_category.id,
        entity_id=entity.id,
    )
    client1 = Account(
        name="client account 1",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        category_id=client_category.id,
        entity_id=entity.id,
    )
    client2 = Account(
        name="client account two",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        category_id=client_category.id,
        entity_id=entity.id,
    )

    session.add_all(
        [
            revenue,
            client1,
            client2,
        ]
    )
    session.flush()

    session.add(
        Balance(
            transaction_date=datetime.now() - relativedelta(years=1),
            transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
            amount=75,
            balance_type=Balance.BalanceType.DEBIT,
            account_id=client1.id,
            entity_id=entity.id,
        )
    )

    invoice = ClientInvoice(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=client2.id,
        entity_id=entity.id,
    )
    session.add(invoice)
    session.commit()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=revenue.id,
        amount=100,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    invoice.line_items.add(line_item1)
    session.add(invoice)
    session.flush()

    invoice.post(session)

    revenue_accounts = revenue_category.account_balances(session)
    revenue_accounts["total"] = -100
    revenue_accounts["accounts"] = [revenue]

    client_accounts = revenue_category.account_balances(session)
    client_accounts["total"] = 175
    client_accounts["accounts"] = [client1, client2]
