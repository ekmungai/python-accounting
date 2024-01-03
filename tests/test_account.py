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
    ReportingPeriod,
    LineItem,
    Tax,
)
from python_accounting.transactions import ClientInvoice
from python_accounting.exceptions import InvalidCategoryAccountTypeError


def test_account_entity(session, entity, currency):
    """Tests the relationship between an account and its associated entity"""

    account = Account(
        name="test account",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(account)
    session.commit()

    account = session.get(Account, account.id)
    assert account.entity.name == "Test Entity"
    assert account.name == "Test Account"


def test_account_validation(session, entity, currency):
    """Tests the validation of account objects"""

    account = Account(
        name="test account",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(account)
    session.flush()

    account = session.get(Account, account.id)
    assert account.account_code == 3000

    account.name = "new test account"
    session.add(account)
    session.flush()

    account = session.get(Account, account.id)
    assert account.account_code == 3000
    assert (
        account.name == "New Test Account"
    )  # changes other than account type do not affect the account code

    account.account_type = Account.AccountType.RECEIVABLE
    session.add(account)
    session.flush()

    account = session.get(Account, account.id)
    assert account.account_code == 50000

    account = Account(
        name="test account three",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(account)
    session.flush()

    account = session.get(Account, account.id)
    account.name == "Test Account Three"
    assert account.account_code == 50002

    category = Category(
        name="Test Category",
        category_account_type=Account.AccountType.BANK,
        entity_id=entity.id,
    )
    session.add(category)
    session.flush()

    account.category_id = category.id
    session.add(account)

    with pytest.raises(InvalidCategoryAccountTypeError) as e:
        session.commit()

    assert str(e.value) == "Cannot assign Receivable Account to Bank Category"


def test_account_isolation(session, entity, currency):
    """Tests the isolation of account objects by entity"""

    year = datetime.today().year
    entity2 = Entity(name="Test Entity Two")
    session.add(entity2)
    session.flush()
    entity2 = session.get(Entity, entity2.id)

    session.add_all(
        [
            Account(
                name="test account one",
                account_type=Account.AccountType.BANK,
                currency_id=currency.id,
                entity_id=entity.id,
            ),
            Account(
                name="test account two",
                account_type=Account.AccountType.RECEIVABLE,
                currency_id=currency.id,
                entity_id=entity2.id,
            ),
        ]
    )
    session.commit()

    accounts = session.scalars(select(Account)).all()

    assert len(accounts) == 1
    assert accounts[0].name == "Test Account One"
    assert accounts[0].account_type == Account.AccountType.BANK
    assert accounts[0].entity.name == "Test Entity"

    account2 = session.get(Account, 3)
    assert account2 == None

    session.entity = entity2
    accounts = session.scalars(select(Account)).all()

    assert len(accounts) == 1
    assert accounts[0].name == "Test Account Two"
    assert accounts[0].account_type == Account.AccountType.RECEIVABLE
    assert accounts[0].entity.name == "Test Entity Two"

    account1 = session.get(Account, 1)
    assert account1 == None


def test_account_recycling(session, entity, currency):
    """Tests the deleting, restoring and destroying functions of the account model"""

    account = Account(
        name="test account one",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(account)
    session.flush()

    account_id = account.id

    session.delete(account)

    account = session.get(Account, account_id)
    assert account == None

    account = session.get(Account, account_id, include_deleted=True)
    assert account != None
    session.restore(account)

    account = session.get(Account, account_id)
    assert account != None

    session.destroy(account)

    account = session.get(Account, account_id)
    assert account == None

    account = session.get(Account, account_id, include_deleted=True)
    assert account != None
    session.restore(account)  # destroyed models canot be restored

    account = session.get(Account, account_id)
    assert account == None

    # HangingTransactionsError #TODO


def test_account_opening_balance(session, entity, currency):
    """Tests an account's opening balance"""

    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test account two",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([account1, account2])
    session.flush()

    date = datetime.now() - relativedelta(years=1)
    session.add_all(
        [
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
                amount=100,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=25,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.SUPPLIER_BILL,
                amount=50,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=account2.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=15,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
        ]
    )
    assert account1.opening_balance(session) == 90
    assert account2.opening_balance(session) == -50

    date -= relativedelta(years=1)
    new_reporting_period = ReportingPeriod(
        calendar_year=date.year,
        period_count=2,
        entity_id=entity.id,
    )
    session.add(new_reporting_period)
    session.commit()
    assert account1.opening_balance(session, date.year) == 0
    assert account2.opening_balance(session, date.year) == 0


def test_account_closing_balance(session, entity, currency):
    """Tests an account's closing balance method"""
    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test account two",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([account1, account2])
    session.flush()

    date = datetime.now() - relativedelta(years=1)
    session.add_all(
        [
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
                amount=100,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=25,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=15,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
        ]
    )
    transaction = Transaction(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account1.id,
        transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.flush()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account2.id,
        amount=25,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    transaction.line_items.add(line_item1)
    session.add(transaction)
    session.flush()

    assert account1.closing_balance(session) == 90
    assert transaction.is_posted == False

    transaction.post(session)

    assert account1.closing_balance(session) == 65
    assert transaction.is_posted == True
    assert (
        account1.closing_balance(session, datetime.now() - relativedelta(days=1)) == 90
    )


def test_account_section_balances(session, entity, currency):
    """Tests accounts' balances aggregation by section"""

    category1 = Category(
        name="Test Category One",
        category_account_type=Account.AccountType.RECEIVABLE,
        entity_id=entity.id,
    )
    category2 = Category(
        name="Test Category Two",
        category_account_type=Account.AccountType.RECEIVABLE,
        entity_id=entity.id,
    )
    category3 = Category(
        name="Test Category Three",
        category_account_type=Account.AccountType.OPERATING_REVENUE,
        entity_id=entity.id,
    )
    category4 = Category(
        name="Test Category Four",
        category_account_type=Account.AccountType.CONTROL,
        entity_id=entity.id,
    )
    session.add_all([category1, category2, category3, category4])
    session.flush()

    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        category_id=category1.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test account two",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        category_id=category2.id,
        entity_id=entity.id,
    )
    account3 = Account(
        name="test account three",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        category_id=category3.id,
        entity_id=entity.id,
    )
    account4 = Account(
        name="test account four",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        category_id=category4.id,
        entity_id=entity.id,
    )
    session.add_all([account1, account2, account3, account4])
    session.flush()

    date = datetime.now() - relativedelta(years=1)
    session.add_all(
        [
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
                amount=150,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=80,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=account1.id,
                entity_id=entity.id,
            ),
        ]
    )
    transaction = ClientInvoice(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account2.id,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.commit()

    tax = Tax(
        name="Output Vat",
        code="OTPT",
        account_id=account4.id,
        rate=10,
        entity_id=entity.id,
    )
    session.add(tax)
    session.flush()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account3.id,
        amount=100,
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    transaction.line_items.add(line_item1)
    session.add(transaction)
    session.flush()

    transaction.post(session)

    receivables_balances = Account.section_balances(
        session, [Account.AccountType.RECEIVABLE]
    )
    assert receivables_balances["opening"] == 70
    assert receivables_balances["movement"] == -110
    assert receivables_balances["closing"] == 180
    assert len(receivables_balances["categories"]) == 2
    assert receivables_balances["categories"][category1.name]["total"] == 70
    assert receivables_balances["categories"][category1.name]["accounts"] == [account1]

    revenues_balances = Account.section_balances(
        session, [Account.AccountType.OPERATING_REVENUE]
    )
    assert revenues_balances["opening"] == 0
    assert revenues_balances["movement"] == 100
    assert revenues_balances["closing"] == -100
    assert len(revenues_balances["categories"]) == 1
    assert revenues_balances["categories"][category3.name]["total"] == -100
    assert revenues_balances["categories"][category3.name]["accounts"] == [account3]

    control_balances = Account.section_balances(session, [Account.AccountType.CONTROL])
    assert control_balances["opening"] == 0
    assert control_balances["movement"] == 10
    assert control_balances["closing"] == -10
    assert len(control_balances["categories"]) == 1
    assert control_balances["categories"][category4.name]["total"] == -10
    assert control_balances["categories"][category4.name]["accounts"] == [account4]


def test_account_transactions(entity, currency):  # TODO
    """Tests an account's Transactions"""
    pass
