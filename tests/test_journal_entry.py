import pytest
from datetime import datetime
from python_accounting.models import Account, Tax, LineItem, Balance
from python_accounting.transactions import JournalEntry
from python_accounting.exceptions import (
    UnbalancedTransactionError,
    MissingMainAccountAmountError,
    InvalidTaxChargeError,
)


def test_journal_entry_ledgers(session, entity, currency):
    """Tests journal entry transaction ledger records"""

    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.INVENTORY,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test account two",
        account_type=Account.AccountType.CONTRA_ASSET,
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

    transaction = JournalEntry(
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
        tax_id=tax.id,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    transaction.line_items.add(line_item1)
    session.add(transaction)
    session.flush()

    transaction.post(session)

    # Tax entries
    assert transaction.ledgers[0].post_account_id == account1.id
    assert transaction.ledgers[0].folio_account_id == account3.id
    assert transaction.ledgers[0].amount == 10
    assert transaction.ledgers[0].entry_type == Balance.BalanceType.CREDIT

    assert transaction.ledgers[1].post_account_id == account3.id
    assert transaction.ledgers[1].folio_account_id == account1.id
    assert transaction.ledgers[1].amount == 10
    assert transaction.ledgers[1].entry_type == Balance.BalanceType.DEBIT

    # Line Item entries
    assert transaction.ledgers[2].post_account_id == account1.id
    assert transaction.ledgers[2].folio_account_id == account2.id
    assert transaction.ledgers[2].amount == 100
    assert transaction.ledgers[2].entry_type == Balance.BalanceType.CREDIT

    assert transaction.ledgers[3].post_account_id == account2.id
    assert transaction.ledgers[3].folio_account_id == account1.id
    assert transaction.ledgers[3].amount == 100
    assert transaction.ledgers[3].entry_type == Balance.BalanceType.DEBIT


def test_compound_journal_entry_ledgers(session, entity, currency):
    """Tests compound journal entry transaction ledger records"""

    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.INVENTORY,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test account two",
        account_type=Account.AccountType.CONTRA_ASSET,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account3 = Account(
        name="test account three",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account4 = Account(
        name="test account four",
        account_type=Account.AccountType.RECONCILIATION,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([account1, account2, account3, account4])
    session.flush()

    transaction = JournalEntry(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
        credited=False,
        main_account_amount=25,
        compound=True,
    )
    session.add(transaction)
    session.commit()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account2.id,
        amount=100,
        credited=True,
        entity_id=entity.id,
    )

    line_item2 = LineItem(
        narration="Test line item two",
        account_id=account3.id,
        amount=150,
        entity_id=entity.id,
    )

    line_item3 = LineItem(
        narration="Test line item three",
        account_id=account4.id,
        amount=75,
        credited=True,
        entity_id=entity.id,
    )

    session.add_all([line_item1, line_item2, line_item3])
    session.flush()

    transaction.line_items.update([line_item1, line_item2, line_item3])
    session.add(transaction)
    session.flush()

    transaction.post(session)

    assert transaction.contribution(session, account1) == 25
    assert transaction.contribution(session, account2) == -100
    assert transaction.contribution(session, account3) == 150
    assert transaction.contribution(session, account4) == -75
    assert transaction.amount == 175


def test_journal_entry_validation(session, entity, currency):
    """Tests the validation of journal entry transactions"""
    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.INVENTORY,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test account two",
        account_type=Account.AccountType.CONTRA_ASSET,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account3 = Account(
        name="test account three",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account4 = Account(
        name="test account four",
        account_type=Account.AccountType.RECONCILIATION,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([account1, account2, account3, account4])
    session.flush()

    transaction = JournalEntry(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
        credited=False,
        # main_account_amount=25,
        compound=True,
    )
    session.add(transaction)
    with pytest.raises(MissingMainAccountAmountError) as e:
        session.commit()
    assert (
        str(e.value)
        == "A Compound Journal Entry Transaction must have a main account amount."
    )

    transaction.main_account_amount = 25
    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account2.id,
        amount=100,
        credited=True,
        entity_id=entity.id,
    )

    line_item2 = LineItem(
        narration="Test line item two",
        account_id=account3.id,
        amount=150,
        credited=False,
        entity_id=entity.id,
    )

    line_item3 = LineItem(
        narration="Test line item three",
        account_id=account4.id,
        amount=85,
        credited=True,
        entity_id=entity.id,
    )

    tax = Tax(
        name="Output Vat",
        code="OTPT",
        account_id=account3.id,
        rate=10,
        entity_id=entity.id,
    )
    session.add(tax)
    session.flush()

    line_item4 = LineItem(
        narration="Test line item four",
        account_id=account4.id,
        amount=10,
        tax_id=tax.id,
        credited=False,
        entity_id=entity.id,
    )

    session.add_all([line_item1, line_item2, line_item3, line_item4])
    session.flush()

    transaction.line_items.update([line_item1, line_item2, line_item3])
    with pytest.raises(UnbalancedTransactionError) as e:
        session.commit()
    assert str(e.value) == "Total Debit amounts do not match total Credit amounts."

    with pytest.raises(InvalidTaxChargeError) as e:
        transaction.line_items.add(line_item4)
    assert str(e.value) == "Compound JournalEntry Transactions cannot be charged Tax."
