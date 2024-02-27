
Python Accounting
==================
[![Build Status](https://github.com/ekmungai/python-accounting/workflows/Python%20package/badge.svg)](https://github.com/ekmungai/python-accounting/actions)

Python Accounting is the world's most comprehensive Double Entry Bookkeeping python library. 
Unlike other similar libraries, Python Accounting focuses on the generation of Financial Reports
compatible with both IFRS and GAAP standards. 

The library is designed to be fully customizable, supports multiple Entities (Companies), Account 
Categorization, Transaction assignment, Opening Balances and Taxation. Transactions are also protected 
against tampering via direct database changes ensuring the integrity of the Ledger. Apart from the standard
set of Financial Reports, the Library also provides convenient Receivable (Client) and Payabale (Supplier) 
such as Account Statements and Schedules, as well as an Aging Schedule for all outstanding balances grouped 
by configurable time periods (Current, 31 - 90 days, 91 - 180 days etc).

This library is a community initiative of [microbooks.io](https://microbooks.io).

## Installation

You can use [pip](https://pip.pypa.io/en/stable/) to install. The library requires python 3.9+.

```bash
pip install python-accounting
```

## Usage
Full documemntation for the library can be found on [readthedocs](https://python-accounting.readthedocs.io/en/latest/).

To use the Library, we first need to configure it.

```python
from python_accounting import config
from python_accounting.models import Base
from sqlalchemy import create_engine

database = config.database
engine = create_engine(database["url"])

Base.metadata.create_all(engine) # run migrations to create tables
```

Now we can create the reporting Entity and its reporting Currency.

```python
from python_accounting.database.session import get_session
from python_accounting.models import Entity, Currency

with get_session(engine) as session:
    entity = Entity(name="Example Company")
    session.add(entity)
    session.commit() # This automatically sets up a Reporting Period for the Entity

    currency = Currency(name="US Dollars", code="USD", entity_id=entity.id)
    session.add(currency)
    session.commit()
```
Next we'll setup the chart of Accounts.

```python
from python_accounting.models import Account

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
opex_account = Account(
    name="Opex Account",
    account_type=Account.AccountType.OPERATING_EXPENSE,
    currency_id=currency.id,
    entity_id=entity.id,
)
expense_account = Account(
    name="Expense Account",
    account_type=Account.AccountType.DIRECT_EXPENSE,
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
    tax_account, 
    bank_account, 
    revenue_account, 
    client_account, 
    supplier_account, 
    opex_account, 
    expense_account,  
    asset_account
])
session.commit()
```
Before we can start creating Transactions, we need some Taxes.

```python
from python_accounting.models import Tax

output_tax = Tax(
    name="Output Vat",
    code="OTPT",
    account_id=tax_account.id, # This account was created earlier
    rate=20,
    entity_id=entity.id,
)
input_tax = Tax(
    name="Input Vat",
    code="INPT",
    account_id=tax_account.id,
    rate=10,
    entity_id=entity.id,
)
session.add_all([output_tax, input_tax])
session.commit()
```

With the Accounts and Taxes in place, we can now prepare some Transactions.

```python
from datetime import datetime 
from python_accounting.transactions import CashSale

cash_sale = CashSale(
    narration="Cash Sale Transaction",
    transaction_date=datetime.now(),
    account_id=bank_account.id,
    entity_id=entity.id,
)
session.add(cash_sale)
session.flush() # Intermediate save does not record the transaction in the Ledger

```
So far the Transaction has only one side of the double entry, so we create a Line Item for the other side:

```python
from python_accounting.models import LineItem

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
cash_sale.post(session) # This posts the Transaction to the Ledger

```
Now the rest of the Transactions.
```python
from python_accounting.transactions import (
    CashSale,
    ClientInvoice,
    CashPurchase,
    SupplierBill,
    ClientReceipt,
)

client_invoice = ClientInvoice(
    narration="Client Invoice Transaction",
    transaction_date=datetime.now(),
    account_id=client_account.id,
    entity_id=entity.id,
)
session.add(client_invoice)
session.flush()

client_invoice_line_item = LineItem(
    narration="Client Invoice line item",
    account_id=revenue_account.id,
    amount=50,
    quantity=3,
    tax_id=output_tax.id,
    entity_id=entity.id,
)
session.add(client_invoice_line_item)
session.flush()

client_invoice.line_items.add(client_invoice_line_item)
session.add(client_invoice)
client_invoice.post(session)

cash_purchase = CashPurchase(
    narration="Cash Purchase Transaction",
    transaction_date=datetime.now(),
    account_id=bank_account.id,
    entity_id=entity.id,
)
session.add(cash_purchase)
session.flush()

cash_purchase_line_item = LineItem(
    narration="Cash Purchase line item",
    account_id=opex_account.id,
    amount=25,
    quantity=4,
    tax_id=output_tax.id,
    entity_id=entity.id,
)
session.add(cash_purchase_line_item)
session.flush()

cash_purchase.line_items.add(cash_purchase_line_item)
session.add(cash_purchase)
cash_purchase.post(session)

supplier_bill = SupplierBill(
    narration="Credit Purchase Transaction",
    transaction_date=datetime.now(),
    account_id=supplier_account.id,
    entity_id=entity.id,
)
session.add(supplier_bill)
session.flush()

supplier_bill_line_item = LineItem(
    narration="Credit Purchase line item",
    account_id=asset_account.id,
    amount=25,
    quantity=4,
    tax_id=output_tax.id,
    entity_id=entity.id,
)
session.add(supplier_bill_line_item)
session.flush()

supplier_bill.line_items.add(supplier_bill_line_item)
session.add(supplier_bill)
supplier_bill.post(session)

journal_entry = JournalEntry(
    narration="Journal Entry Transaction",
    transaction_date=datetime.now(),
    account_id=bank_account.id,
    entity_id=entity.id,
)
session.add(journal_entry)
session.flush() 

journal_entry_line_item = LineItem(
    narration="Journal Entry line item",
    account_id=expense_account.id,
    amount=30,
    entity_id=entity.id,
)
session.add(journal_entry_line_item)
session.flush()

journal_entry.line_items.add(journal_entry_line_item)
session.add(journal_entry)
journal_entry.post(session)

client_receipt = ClientReceipt(
    narration="Client Receipt Transaction",
    transaction_date=datetime.now(),
    account_id=client_account.id,
    entity_id=entity.id,
)
session.add(client_receipt)
session.flush()

client_receipt_line_item = LineItem(
    narration="Client Receipt line item",
    account_id=bank_account.id,
    amount=50,
    quantity=1,
    entity_id=entity.id,
)
session.add(client_receipt_line_item)
session.flush()

client_receipt.line_items.add(client_receipt_line_item)
session.add(client_receipt)
client_receipt.post(session)
```
We can assign the Receipt to partially clear the Invoice above:

```python
from python_accounting.models import Assignment


print(client_invoice.cleared(session)) # 0: The Invoice has not been cleared at all
print(client_receipt.balance(session)) # 60: The Receipt has not been assigned

assignment = Assignment(
    assignment_date=datetime.now(),
    transaction_id=client_receipt.id,
    assigned_id=client_invoice.id,
    assigned_type=client_invoice.__class__.__name__,
    entity_id=entity.id,
    amount=15,
)
session.add(assignment)
session.commit()

print(client_invoice.cleared(session)) # 15 
print(client_receipt.balance(session)) # 45

```
We are now ready to generate some reports, starting with the Income Statement (Profit and Loss).

```python
from python_accounting.reports import IncomeStatement

income_statement = IncomeStatement(session) 

print(income_statement)

               Example Company
               Income Statement
 For the period: 01, Jan 2024 to 23, Feb 2024

Operating Revenues
    Operating Revenue                250.0000 (100 cash sales + 150 credit sales)

Operating Expenses
    Operating Expense                100.0000 (cash purchase)
                              _______________
Gross Profit                         150.0000


Non Operating Revenues
    Non Operating Revenue              0.0000
                              _______________
Total Revenue                        150.0000


Non Operating Expenses
    Direct Expense                    30.0000
                              _______________
Total Expenses                        30.0000

                              _______________
Net Profit                           120.0000
                              ===============
```

The Balance Sheet.

```python
from python_accounting.reports import BalanceSheet

balance_sheet = BalanceSheet(session) 

print(balance_sheet)

               Example Company
                Balance Sheet
 For the period: 01, Jan 2024 to 23, Feb 2024

Assets
    Non Current Asset                100.0000 (asset purchase)
    Bank                              30.0000 (120 cash sale - 110 cash purchase + 50 
                                              client receipt - 30 journal entry)
    Receivable                       130.0000 (150 credit sale + 30 Tax - 50 client receipt)
                              _______________
Total Assets                         260.0000


Liabilities
    Control                           30.0000 (Taxes: 20 cash sale + 30 credit sale - 10 cash 
                                              purchase - 10 credit purchase)
    Payable                          110.0000 (100 credit purchase + 10 Tax)
                              _______________
Total Liabilities                    140.0000

                              _______________
Net Assets                           120.0000
                              ===============

Equity
    Income Statement                 120.0000
                              _______________
Total Equity                         120.0000
                              ===============
```
And finally The Cashflow Statement.

```python
from python_accounting.reports import CashflowStatement

cashflow_statememt = CashflowStatement(session) 

print(cashflow_statememt)

                 Test Entity
              Cashflow Statement
 For the period: 01, Jan 2024 to 23, Feb 2024

Operating Cash Flow
    Net Profit                       120.0000
    Receivables                     -130.0000
    Payables                         110.0000
    Taxation                          30.0000
                              _______________
 Total Operating Cash Flow           130.0000


Investment Cash Flow
    Non Current Assets              -100.0000 (Asset Purchase)
                              _______________
 Total Investment Cash Flow         -100.0000


Financing Cash Flow
    Equity                             0.0000
                              _______________
 Total Financing Cash Flow             0.0000


Net Cash Flow
    Beginning Cash Balance             0.0000
    Net Cash Flow                     30.0000
                              _______________
Ending Cash Balance                   30.0000
                              ===============
                              _______________
Cashbook Balance                      30.0000
                              ===============
```
## Supported Databases (Fully tested)

- MySql/MariaDb
- Postgres
- Sqlite (testing)

## Changelog

Please see [CHANGELOG](https://github.com/ekmungai/python-accounting/blob/main/CHANGELOG) for more information about recent changes.

## Contributing

Please see [CONTRIBUTING](https://github.com/ekmungai/python-accounting/blob/main/CONTRIBUTING) for more information about how to get involved.

## License

This software is distributed for free under the MIT License. Please see [LICENCE](https://github.com/ekmungai/python-accounting/blob/main/LICENSE) for more information.

