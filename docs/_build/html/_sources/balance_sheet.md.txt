## Balance Sheet
The Balance Sheet, also known as the Statement of Financial position shows the financial health of the entity by comparing the combined balances of asset Accounts to those of liability and equity Accounts.

**Parameters**: 
- session (Session): The accounting session.
- end_date (datetime): The latest transaction date for Transaction amounts to be included in the statement.

**Returns** An `BalanceSheet` with:
- sections (StrEnum): The sections of the Balance Sheet.
- results (StrEnum): The results of the Balance Sheet.
- accounts (dict): The Accounts in the sections of the report, by Account category.
- balances (dict): The total balances of the Accounts in the sections of the report, by Account category.
- totals (dict): The Total balances of Accounts in the sections of the report.
- result_amounts (dict): The amounts results of the report.

 
**Example**
```python

balance_sheet = BalanceSheet(session) 

print(balance_sheet)

               Example Company
                Balance Sheet
 For the period: 01, Jan 2024 to 23, Feb 2024

Assets
    Non Current Asset                120.0000 
    Receivables                       70.0000 
    Bank                              50.0000 
                              _______________
Total Assets                         240.0000


Liabilities
    Control                           20.0000 
    Payable                          120.0000 
                              _______________
Total Liabilities                    140.0000

                              _______________
Net Assets                           100.0000
                              ===============

Equity
    Income Statement                 100.0000
                              _______________
Total Equity                         100.0000
                              ===============
```