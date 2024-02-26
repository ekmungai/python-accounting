## Tax Inclusive Transactions
Under ordinary circumstances, the Tax amount is added to the amount of the Transaction to arrive at the total. In some cases however, the tax amount is included in the Transaction amount already which requires different accounting treatment. This Example will demonstrate how to create one of each kind of transaction.

**Tax Exclusive**  
This Transaction will have the Tax amount added on top of the Transaction amount. We first need the Accounts involved.

```python
from python_accounting.models import Account

with get_session(engine) as session:
    tax_account = Account(
        name="Tax Account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    bank_account = Account(
        name="Bank Account",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    revenue_account = Account(
        name="Revenue Account",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add_all([
        tax_account, 
        bank_account, 
        revenue_account, 
    ])
    session.commit()
```
Next we'll create the Tax.

```python
from python_accounting.models import Tax

with get_session(engine) as session:
    output_tax = Tax(
        name="Input Vat",
        code="INPT",
        account_id=tax_account.id,
        rate=10,
        entity_id=entity.id,
    )
    session.add_all(output_tax, input_tax)
    session.commit()
```
Now we're ready to create the Tax exclusive Transaction. By default, the Library treats Transactions as Tax Exclusive. 

```python
from datetime import datetime 
from python_accounting.models import Transaction, LineItem
from python_accounting.transactions import CashSale

with get_session(engine) as session:
    cash_sale = CashSale(
        narration="Cash Sale Transaction",
        transaction_date=datetime.now(),
        account_id=bank_account.id,
        entity_id=entity.id,
    )
    session.add(cash_sale)
    session.flush() 

    cash_sale_line_item = LineItem(
        narration="Cash Sale line item",
        account_id=revenue_account.id,
        amount=100,
        tax_id=output_tax.id,
        entity_id=entity.id,
    )
    session.add(cash_sale_line_item)
    session.flush()

    cash_sale.line_items.add(cash_sale_line_item)
    session.add(cash_sale)
    cash_sale.post(session)

    print(bank_account.closing_balance(session)) # 110
    print(revenue_account.closing_balance(session)) # -100
    print(tax_account.closing_balance(session)) # -10
```


**Tax Inclusive**  
The procedure for a Tax Inclusive Transaction is identical to the one above, with the only difference being that the Line Item is explicitly marked as being tax inclusive.

```python
from datetime import datetime 
from python_accounting.models import Transaction, LineItem
from python_accounting.transactions import CashSale

with get_session(engine) as session:
    cash_sale = CashSale(
        narration="Cash Sale Transaction",
        transaction_date=datetime.now(),
        account_id=bank_account.id,
        entity_id=entity.id,
    )
    session.add(cash_sale)
    session.flush() 

    cash_sale_line_item = LineItem(
        narration="Cash Sale line item",
        account_id=revenue_account.id,
        amount=100,
        tax_id=output_tax.id,
        tax_inclusive=True, # <- Turn on Tax Inclusive for the Line Item
        entity_id=entity.id,
    )
    session.add(cash_sale_line_item)
    session.flush()

    cash_sale.line_items.add(cash_sale_line_item)
    session.add(cash_sale)
    cash_sale.post(session)

    print(bank_account.closing_balance(session)) # 100
    print(revenue_account.closing_balance(session)) # -90.9091
    print(tax_account.closing_balance(session)) # -9.0909
```