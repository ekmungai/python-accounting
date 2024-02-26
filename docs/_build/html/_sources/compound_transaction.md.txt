## Compound Transactions
By default, the library enforces the double entry principle by posting the amounts in a Transaction's Line Items to the opposite side of the ledger from that of its main Account. As such each Transaction type has a fixed setting about to which side of the main Account the amount should be posted. 

:warning: While its technically possible to create Transaction objects directly, doing so would bypass the validation rules built into the derived Transaction classes which could lead to incorrect bookkeeping and is therefore strongly discouraged.

The Journal Entry is the only Transaction type that allows you to specify whether the amount should be credited to the main Account or not. In a standard Journal Entry Transaction, all the Line Item amounts are posted to the opposite side of the ledger from that specified for the main Account, i.e if `credited=True` all the Line Item Accounts will have the Line Item amounts posted to the debit side of the ledger and vice versa. 

**Standard Journal Entry**  
This Transaction will post the total amount to the debit side of the main Account, and the Line Item amounts to the credit side of each Line Item Account. 

First we'll create some Accounts.

```python
from python_accounting.models import Account

with get_session(engine) as session:
    bank_account = Account(
        name="Bank Account",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    client_account = Account(
        name="Client Account",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    supplier_account = Account(
        name="Supplier Account",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    asset_account = Account(
        name="Asset Account",
        account_type=Account.AccountType.NON_CURRENT_ASSET,
        currency_id=currency.id,
        entity_id=entity.id,
    )    

    session.add_all([
        bank_account, 
        client_account, 
        supplier_account, 
        asset_account
    ])
    session.commit()
```
The Journal Entry's `credited` property is set to True by default, so for this example we'll turn it to False. 

```python
from datetime import datetime 
from python_accounting.models import Transaction, LineItem
from python_accounting.transactions import JournalEntry

with get_session(engine) as session:
    journal_entry = JournalEntry(
        narration="Journal Entry Transaction",
        transaction_date=datetime.now(),
        account_id=bank_account.id,
        entity_id=entity.id,
        credited=False # <- Debit the main (bank) account
    )
    session.add(journal_entry)
    session.flush() 

    client_account_line_item = LineItem(
        narration="Client Account line item",
        account_id=client_account.id,
        amount=30,
        entity_id=entity.id,
    )
    supplier_account_line_item = LineItem(
        narration="Supplier Account line item",
        account_id=supplier_account.id,
        amount=15,
        entity_id=entity.id,
    )
    asset_account_line_item = LineItem(
        narration="Asset Account line item",
        account_id=asset_account.id,
        amount=10,
        entity_id=entity.id,
    )
    session.add_all([
        client_account_line_item,
        supplier_account_line_item,
        asset_account_line_item
    ])
    session.flush()

    journal_entry.line_items.add(client_account_line_item)
    journal_entry.line_items.add(supplier_account_line_item)
    journal_entry.line_items.add(asset_account_line_item)
    session.add(journal_entry)
    journal_entry.post(session)

    print(bank_account.closing_balance(session)) # 55
    print(client_account.closing_balance(session)) # -30
    print(supplier_account.closing_balance(session)) # -15
    print(asset_account.closing_balance(session)) # -10
```

**Compound Journal Entry**  
Sometimes however, you might want to post line item amounts to different sides of the ledger for different accounts. To accomplish this, you turn on the `compound` property of the Transaction and also specify a `main_account_amount`. This is because as opposed to the simple case above, different amounts are being posted to different sides of the ledger by the Line Items and its therefore not obvious what amount should be posted to the main account. On the other side, we specify the side to which each Line Item Account will have their amount posted, which is debit by default. 

Needless to say the totals of amounts posted to the debit and credit side of the ledger must equal exactly otherwise the Transaction will throw an error.


```python
from datetime import datetime 
from python_accounting.models import Transaction, LineItem
from python_accounting.transactions import JournalEntry

with get_session(engine) as session:
    journal_entry = JournalEntry(
        narration="Journal Entry Transaction",
        transaction_date=datetime.now(),
        account_id=bank_account.id,
        entity_id=entity.id,
        compound=True, # <- Turn on compound flag
        credited=False, 
        main_account_amount=25, # <- Specify how much to post to the main (bank) account
    )
    session.add(journal_entry)
    session.flush() 

    client_account_line_item = LineItem(
        narration="Client Account line item",
        account_id=client_account.id,
        credited=True, # <- Specify to credit this line item's amount to is account
        amount=30,
        entity_id=entity.id,
    )
    supplier_account_line_item = LineItem(
        narration="Supplier Account line item",
        account_id=client_account.id,
        amount=15,
        entity_id=entity.id,
    )
    asset_account_line_item = LineItem(
        narration="Asset Account line item",
        account_id=asset_account.id,
        credited=True, # <- Specify to credit this line item's amount to is account
        amount=10,
        entity_id=entity.id,
    )
    session.add_all([
        client_account_line_item,
        supplier_account_line_item,
        asset_account_line_item
    ])
    session.flush()

    journal_entry.line_items.add(client_account_line_item)
    journal_entry.line_items.add(supplier_account_line_item)
    journal_entry.line_items.add(asset_account_line_item)
    session.add(journal_entry)
    journal_entry.post(session)

    print(bank_account.closing_balance(session)) # 25
    print(client_account.closing_balance(session)) # -30
    print(supplier_account.closing_balance(session)) # 15
    print(asset_account.closing_balance(session)) # -10
```
