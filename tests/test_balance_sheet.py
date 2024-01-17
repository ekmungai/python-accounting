from datetime import datetime
from dateutil.relativedelta import relativedelta
from python_accounting.reports import BalanceSheet
from python_accounting.models import (
    Account,
    Tax,
    LineItem,
    Transaction,
    Category,
    Balance,
)


def test_balance_sheet(session, entity, currency):
    """Tests the generation of an entity's balance sheet"""

    category = Category(
        name="Test Category",
        category_account_type=Account.AccountType.RECEIVABLE,
        entity_id=entity.id,
    )
    session.add(category)
    session.commit()

    bank = Account(
        name="test account one",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    revenue = Account(
        name="test account two",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    control = Account(
        name="test account three",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    client = Account(
        name="test account four",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    client2 = Account(
        name="test account five",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        category_id=category.id,
        entity_id=entity.id,
    )
    income = Account(
        name="test account six",
        account_type=Account.AccountType.NON_OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    supplier = Account(
        name="test account seven",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    cogs = Account(
        name="test account eight",
        account_type=Account.AccountType.OPERATING_EXPENSE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    inventory = Account(
        name="test account nine",
        account_type=Account.AccountType.INVENTORY,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    liability = Account(
        name="test account ten",
        account_type=Account.AccountType.CURRENT_LIABILITY,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all(
        [
            bank,
            revenue,
            control,
            client,
            client2,
            income,
            supplier,
            cogs,
            inventory,
            liability,
        ]
    )
    session.flush()

    balance = Balance(
        transaction_date=datetime.now() - relativedelta(years=1),
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        amount=100,
        balance_type=Balance.BalanceType.DEBIT,
        account_id=inventory.id,
        entity_id=entity.id,
    )
    session.add(balance)
    session.commit()

    statement = BalanceSheet(session)

    print(statement)
