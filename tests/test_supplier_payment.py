import pytest
from datetime import datetime
from python_accounting.models import Account, Tax, LineItem, Balance
from python_accounting.transactions import SupplierPayment
from python_accounting.exceptions import (
    InvalidMainAccountError,
    InvalidLineItemAccountError,
)


def test_supplier_payment_ledgers(session, entity, currency):
    """Tests supplier payment transaction ledger records"""

    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test account two",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([account1, account2])
    session.flush()

    transaction = SupplierPayment(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.commit()

    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account2.id,
        amount=100,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    transaction.line_items.add(line_item1)
    session.add(transaction)
    session.flush()

    transaction.post(session)

    # Line Item entries
    assert transaction.ledgers[0].post_account_id == account1.id
    assert transaction.ledgers[0].folio_account_id == account2.id
    assert transaction.ledgers[0].amount == 100
    assert transaction.ledgers[0].entry_type == Balance.BalanceType.DEBIT

    assert transaction.ledgers[1].post_account_id == account2.id
    assert transaction.ledgers[1].folio_account_id == account1.id
    assert transaction.ledgers[1].amount == 100
    assert transaction.ledgers[1].entry_type == Balance.BalanceType.CREDIT


def test_supplier_payment_validation(session, entity, currency):
    """Tests the validation of supplier payment transactions"""
    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.INVENTORY,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test account two",
        account_type=Account.AccountType.RECONCILIATION,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add_all([account1, account2])
    session.flush()

    transaction = SupplierPayment(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
    )
    session.add(transaction)

    with pytest.raises(InvalidMainAccountError) as e:
        session.commit()
    assert (
        str(e.value) == "SupplierPayment Transaction main Account be of type Payable."
    )
    account1.account_type = Account.AccountType.PAYABLE
    line_item1 = LineItem(
        narration="Test line item one",
        account_id=account2.id,
        amount=100,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    with pytest.raises(InvalidLineItemAccountError) as e:
        transaction.line_items.add(line_item1)
    assert (
        str(e.value)
        == """SupplierPayment Transaction Line Item Account type must
         be one of: Bank."""
    )
