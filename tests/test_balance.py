import pytest
from datetime import datetime
from dateutil.relativedelta import relativedelta
from .conftest import engine, entity, session
from sqlalchemy import select
from python_accounting.models import (
    Balance,
    Entity,
    Transaction,
    Account,
    ReportingPeriod,
)
from python_accounting.exceptions import (
    InvalidBalanceAccountError,
    InvalidBalanceTransactionError,
    NegativeAmountError,
    InvalidBalanceDateError,
)


def test_balance_entity(entity, session, currency):
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
    assert balance.transaction_no == f"4USD{datetime.today().year}"
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
    with pytest.raises(InvalidBalanceDateError):
        session.commit()

    balance.transaction_date = datetime.now() - relativedelta(years=1)
    session.add(balance)

    account.account_type = Account.AccountType.OPERATING_REVENUE
    session.add(account)

    with pytest.raises(InvalidBalanceAccountError):
        session.commit()

    account.account_type = Account.AccountType.RECEIVABLE
    session.add(account)
    session.flush()

    balance.transaction_type = Transaction.TransactionType.CREDIT_NOTE
    session.add(balance)
    with pytest.raises(InvalidBalanceTransactionError):
        session.commit()

    balance.transaction_type = Transaction.TransactionType.JOURNAL_ENTRY
    balance.amount = -1
    session.add(balance)

    with pytest.raises(NegativeAmountError):
        session.commit()


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