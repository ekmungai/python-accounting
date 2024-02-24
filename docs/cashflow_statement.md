## Cashflow Statement
The Cashflow Statement links the Income Statement to the Balance Sheet by reconciling the performance of the Entity with changes in the balances of assets, liabilities, equity and the balances in the cashbook.

**Parameters**: 
- session (Session): The accounting session.
- start_date (datetime): The earliest transaction date for Transaction amounts to be included in the statement.
- end_date (datetime): The latest transaction date for Transaction amounts to be included in the statement.

**Returns** An `CashFlowStatement` with:
- sections (StrEnum): The sections of the Cashflow Statement.
- results (StrEnum): The results of the Cashflow Statement.
- accounts (dict): The Accounts in the sections of the report, by Account category.
- balances (dict): The total balances of the Accounts in the sections of the report, by Account category.
- totals (dict): The Total balances of Accounts in the sections of the report.
- result_amounts (dict): The amounts results of the report.

 
**Example**
```python

cashflow_statememt = BalanceSheet(session) 

print(cashflow_statememt)

                 Test Entity
              Cashflow Statement
 For the period: 01, Jan 2024 to 23, Feb 2024

Operating Cash Flow
    Net Profit                       100.0000
    Receivables                      -70.0000
    Payables                         120.0000
    Taxation                          20.0000
                              _______________
 Total Operating Cash Flow           170.0000


Investment Cash Flow
    Non Current Assets              -120.0000
                              _______________
 Total Investment Cash Flow         -120.0000


Financing Cash Flow
    Equity                             0.0000
                              _______________
 Total Financing Cash Flow             0.0000


Net Cash Flow
    Beginning Cash Balance             0.0000
    Net Cash Flow                     50.0000
                              _______________
Ending Cash Balance                   50.0000
                              ===============
                              _______________
Cashbook Balance                      50.0000
                              ===============
```