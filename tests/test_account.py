import pytest
from datetime import datetime
from sqlalchemy import select
from python_accounting.models import Account, Currency, Category, Entity
from python_accounting.exceptions import InvalidCategoryAccountTypeError


def test_account_entity(entity, session, currency):
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
    assert account.account_code == 3001

    account.name = "new test account"
    session.add(account)
    session.flush()

    account = session.get(Account, account.id)
    assert account.account_code == 3001
    assert (
        account.name == "New Test Account"
    )  # changes other than account type do not affect the account code

    account.account_type = Account.AccountType.RECEIVABLE
    session.add(account)
    session.flush()

    account = session.get(Account, account.id)
    assert account.account_code == 50001

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


def test_account_opening_balance(entity, currency):  # TODO
    """Tests an account's opening balance property"""
    pass


def test_account_closing_balance_method(entity, currency):  # TODO
    """Tests an account's opening balance property"""
    pass


def test_account_section_balances(entity, currency):  # TODO
    """Tests accounts' balances aggregation by section"""
    pass


def test_account_section_balance_movement(entity, currency):  # TODO
    """Tests changes in accounts' balances aggregation by section"""
    pass


def test_account_transactions(entity, currency):  # TODO
    """Tests an account's Transactions"""
    pass


def test_opening_trial_balance(entity, currency):  # TODO
    """Tests the Chart of Accounts Opening Trial Balance"""
    pass
