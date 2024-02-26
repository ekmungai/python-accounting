import pytest
from datetime import datetime
from python_accounting.models import Account, Tax, LineItem, Balance
from python_accounting.transactions import CashSale
from python_accounting.exceptions import (
    InvalidMainAccountError,
    InvalidLineItemAccountError,
)


def test_cash_sale_ledgers(session, entity, currency):
    """Tests client invoice transaction ledger records"""

    account1 = Account(
        name="test account one",
        account_type=Account.AccountType.BANK,
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

    transaction = CashSale(
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
    assert transaction.ledgers[0].entry_type == Balance.BalanceType.DEBIT

    assert transaction.ledgers[1].post_account_id == account3.id
    assert transaction.ledgers[1].folio_account_id == account1.id
    assert transaction.ledgers[1].amount == 10
    assert transaction.ledgers[1].entry_type == Balance.BalanceType.CREDIT

    # Line Item entries
    assert transaction.ledgers[2].post_account_id == account1.id
    assert transaction.ledgers[2].folio_account_id == account2.id
    assert transaction.ledgers[2].amount == 100
    assert transaction.ledgers[2].entry_type == Balance.BalanceType.DEBIT

    assert transaction.ledgers[3].post_account_id == account2.id
    assert transaction.ledgers[3].folio_account_id == account1.id
    assert transaction.ledgers[3].amount == 100
    assert transaction.ledgers[3].entry_type == Balance.BalanceType.CREDIT


def test_cash_sale_validation(session, entity, currency):
    """Tests the validation of cash sale transactions"""
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

    transaction = CashSale(
        narration="Test transaction one",
        transaction_date=datetime.now(),
        account_id=account1.id,
        entity_id=entity.id,
    )
    session.add(transaction)

    with pytest.raises(InvalidMainAccountError) as e:
        session.commit()
    assert str(e.value) == "CashSale Transaction main Account be of type Bank."

    account1.account_type = Account.AccountType.BANK
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
        == """CashSale Transaction Line Item Account type must
         be one of: Operating Revenue."""
    )
