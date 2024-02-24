## Income Statement
The Income Statement, also known as the Profit and Loss statement shows the performance of the entity by subtracting the combined balances of expense accounts from that of income accounts. The end result is the profit made by the Entity for the given period.

**Parameters**: 
- session (Session): The accounting session.
- start_date (datetime): The earliest transaction date for Transaction amounts to be included in the statement.
- end_date (datetime): The latest transaction date for Transaction amounts to be included in the statement.

**Returns** An `IncomeStatement` with:
- sections (StrEnum): The sections of the Income Statement.
- results (StrEnum): The results of the Income Statement.
- accounts (dict): The Accounts in the sections of the report, by Account category.
- balances (dict): The total balances of the Accounts in the sections of the report, by Account category.
- totals (dict): The Total balances of Accounts in the sections of the report.
- result_amounts (dict): The amounts results of the report.

 
**Example**
```python

statement = IncomeStatement(session)

print(statement)

               Example Company
               Income Statement
 For the period: 01, Jan 2024 to 23, Feb 2024

Operating Revenues
    Operating Revenue                200.0000 

Operating Expenses
    Operating Expense                100.0000 
                              _______________
Gross Profit                         100.0000


Non Operating Revenues
    Non Operating Revenue              0.0000
                              _______________
Total Revenue                        100.0000


Non Operating Expenses
                              _______________
Total Expenses                         0.0000

                              _______________
Net Profit                           100.0000
                              ===============
```