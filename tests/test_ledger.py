from datetime import datetime
from python_accounting.models import (
    Ledger,
    Account,
    Transaction,
    LineItem,
)


def test_ledger_entity(session, entity, currency):
    """Tests the relationship between a ledger and its associated entity"""

    account1 = Account(
        name="test ledger account",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    account2 = Account(
        name="test line item account",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add_all([account1, account2])

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
        amount=10,
        entity_id=entity.id,
    )
    session.add(line_item1)
    session.flush()

    transaction.line_items.add(line_item1)
    session.add(transaction)
    session.flush()

    Ledger.post(session, transaction)

    ledger = transaction.ledgers[0]
    assert ledger.entity.name == "Test Entity"
    assert ledger.post_account.name == "Test Ledger Account"
    assert ledger.folio_account.name == "Test Line Item Account"
    assert ledger.line_item.amount == 10
