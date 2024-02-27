import pytest
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from python_accounting.models import (
    Balance,
    Entity,
    Transaction,
    Account,
)
from python_accounting.exceptions import (
    InvalidBalanceAccountError,
    InvalidBalanceTransactionError,
    NegativeValueError,
    InvalidBalanceDateError,
)


def test_balance_entity(session, entity, currency):
    """Tests the relationship between a balance and its associated entity"""
    account = Account(
        name="test account",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)
    session.flush()

    balance = Balance(
        transaction_date=datetime.now() - relativedelta(years=1),
        transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
        amount=100,
        balance_type=Balance.BalanceType.DEBIT,
        account_id=account.id,
        entity_id=entity.id,
    )
    session.add(balance)
    session.commit()

    balance = session.get(Balance, balance.id)
    assert balance.transaction_no == f"{account.id}USD{datetime.today().year}"
    assert balance.entity.name == "Test Entity"


def test_balance_validation(session, entity, currency):
    """Tests the validation of balance objects"""

    account = Account(
        name="test account",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)
    session.flush()

    balance = Balance(
        transaction_date=datetime.now(),
        transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
        amount=100,
        balance_type=Balance.BalanceType.DEBIT,
        account_id=account.id,
        entity_id=entity.id,
    )
    session.add(balance)
    with pytest.raises(InvalidBalanceDateError) as e:
        session.commit()
    assert (
        str(e.value)
        == """Transaction date must be earlier than the first day of the Balance's Reporting Period."""
    )

    balance.transaction_date = datetime.now() - relativedelta(years=1)
    session.add(balance)

    account.account_type = Account.AccountType.OPERATING_REVENUE
    session.add(account)

    print(account.account_type)
    with pytest.raises(InvalidBalanceAccountError) as e:
        session.commit()
    assert str(e.value) == "Income Statement Accounts cannot have an opening balance."

    account.account_type = Account.AccountType.RECEIVABLE
    session.add(account)
    session.flush()

    balance.transaction_type = Transaction.TransactionType.CREDIT_NOTE
    session.add(balance)

    with pytest.raises(InvalidBalanceTransactionError) as e:
        session.commit()
    assert (
        str(e.value)
        == "Balance Transaction must be one of Client Invoice, Supplier Bill or Journal Entry."
    )

    balance.transaction_type = Transaction.TransactionType.JOURNAL_ENTRY
    balance.amount = -1
    session.add(balance)

    with pytest.raises(NegativeValueError) as e:
        session.commit()
    assert str(e.value) == "Balance amount cannot be negative."


def test_balance_isolation(session, entity, currency):
    """Tests the isolation of balance objects by entity"""

    account = Account(
        name="test account",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)
    session.flush()

    entity2 = Entity(name="Test Entity Two")
    session.add(entity2)
    session.flush()
    entity2 = session.get(Entity, entity2.id)

    session.add_all(
        [
            Balance(
                transaction_date=datetime.now() - relativedelta(years=1),
                transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
                amount=100,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=account.id,
                entity_id=entity.id,
            ),
            Balance(
                transaction_date=datetime.now() - relativedelta(years=1),
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=150,
                balance_type=Balance.BalanceType.DEBIT,
                account_id=account.id,
                entity_id=entity2.id,
            ),
        ]
    )
    session.commit()

    balances = session.scalars(select(Balance)).all()

    assert len(balances) == 1
    assert balances[0].transaction_type == Transaction.TransactionType.CLIENT_INVOICE
    assert balances[0].amount == 100
    assert balances[0].entity.name == "Test Entity"

    balance2 = session.get(Balance, 2)
    assert balance2 == None

    session.entity = entity2
    balances = session.scalars(select(Balance)).all()

    assert len(balances) == 1
    assert balances[0].transaction_type == Transaction.TransactionType.JOURNAL_ENTRY
    assert balances[0].amount == 150
    assert balances[0].entity.name == "Test Entity Two"

    balance1 = session.get(Balance, 1)
    assert balance1 == None


def test_balance_recycling(session, entity, currency):
    """Tests the deleting, restoring and destroying functions of the balance model"""

    account = Account(
        name="test account",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)
    session.flush()

    balance = Balance(
        transaction_date=datetime.now() - relativedelta(years=1),
        transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
        amount=100,
        balance_type=Balance.BalanceType.DEBIT,
        account_id=account.id,
        entity_id=entity.id,
    )
    session.add(balance)
    session.flush()

    balance_id = balance.id

    session.delete(balance)

    balance = session.get(Balance, balance_id)
    assert balance == None

    balance = session.get(Balance, balance_id, include_deleted=True)
    assert balance != None
    session.restore(balance)

    balance = session.get(Balance, balance_id)
    assert balance != None

    session.destroy(balance)

    balance = session.get(Balance, balance_id)
    assert balance == None

    balance = session.get(Balance, balance_id, include_deleted=True)
    assert balance != None
    session.restore(balance)  # destroyed models canot be restored

    balance = session.get(Balance, balance_id)
    assert balance == None


def test_opening_trial_balance(session, entity, currency):
    """Tests the Chart of Accounts Opening Trial Balance"""
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
            Balance(
                transaction_date=date,
                transaction_type=Transaction.TransactionType.JOURNAL_ENTRY,
                amount=40,
                balance_type=Balance.BalanceType.CREDIT,
                account_id=account2.id,
                entity_id=entity.id,
            ),
        ]
    )
    opening_trial_balance = Balance.opening_trial_balance(session)

    assert opening_trial_balance["debits"] == 90
    assert opening_trial_balance["credits"] == -90
    assert opening_trial_balance["accounts"] == [account1, account2]
