## Bulk Assignment
Rather than assigning a Receipt or Payment to each Transaction it clears, `bulk_assign` allocates its amount to the outstanding clearable Transactions of its main Account, oldest first, until the amount runs out.

This example carries on from the `session`, `entity` and `currency` created in the Usage section of the README.

```python
from datetime import datetime, timedelta
from python_accounting.models import Account, LineItem
from python_accounting.transactions import ClientInvoice, ClientReceipt

client_account = Account(
    name="Client Account",
    account_type=Account.AccountType.RECEIVABLE,
    currency_id=currency.id,
    entity_id=entity.id,
)
revenue_account = Account(
    name="Revenue Account",
    account_type=Account.AccountType.OPERATING_REVENUE,
    currency_id=currency.id,
    entity_id=entity.id,
)
bank_account = Account(
    name="Bank Account",
    account_type=Account.AccountType.BANK,
    currency_id=currency.id,
    entity_id=entity.id,
)
session.add_all([client_account, revenue_account, bank_account])
session.commit()


def post(transaction_type, date, main_account, line_account, amount):
    transaction = transaction_type(
        narration="Bulk assignment example",
        transaction_date=date,
        account_id=main_account.id,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.flush()

    line_item = LineItem(
        narration="Bulk assignment line item",
        account_id=line_account.id,
        amount=amount,
        entity_id=entity.id,
    )
    session.add(line_item)
    session.flush()

    transaction.line_items.add(line_item)
    session.add(transaction)
    transaction.post(session)
    return transaction


now = datetime.now()
oldest = post(ClientInvoice, now - timedelta(seconds=2), client_account, revenue_account, 100)
newest = post(ClientInvoice, now - timedelta(seconds=1), client_account, revenue_account, 100)
receipt = post(ClientReceipt, now, client_account, bank_account, 150)

receipt.bulk_assign(session)
session.commit()

print(oldest.cleared(session)) # 100
print(newest.cleared(session)) # 50
print(receipt.balance(session)) # 0
```
