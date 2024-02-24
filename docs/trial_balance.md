## Trial Balance
The Trial Balance, compares the closing balances of all accounts in the chart, debits against credits categorised as either Income Statement or Balance Sheet accounts. If the totals match then the books of the Entity have been recorded in accordance with the double entry principle.

**Parameters**: 
- session (Session): The accounting session.
- end_date (datetime): The latest transaction date for Transaction amounts to be included in the statement.

**Returns** An `TrialBalance` with:
- sections (StrEnum): The sections of the Balance Sheet.
- results (StrEnum): The results of the Balance Sheet.
- accounts (dict): The Accounts in the sections of the report, by Account category.
- balances (dict): The total balances of the Accounts in the sections of the report, by Account category.
- totals (dict): The Total balances of Accounts in the sections of the report.
- result_amounts (dict): The amounts results of the report.

 
**Example**
```python
trial_balance = TrialBalance(session)

print(trial_balance)

                 Test Entity
                Trial Balance
 For the period: 01, Jan 2024 to 24, Feb 2024

Income Statement
    Operating Revenue               -420.0000
    Non Operating Revenue            -50.0000
    Operating Expense                100.0000
    Direct Expense                    65.0000
    Overhead Expense                  40.0000
                              _______________
 Total Income Statement             -265.0000


Balance Sheet
    Non Current Asset                100.0000
    Inventory                        100.0000
    Bank                             374.5000
    Receivable                        22.0000
    Control                           -4.5000
    Current Liability               -100.0000
    Payable                         -220.0000
    Equity                           -77.0000
    Reconciliation                    70.0000
                              _______________
 Total Balance Sheet                 265.0000

                              _______________
Total Debits                         871.5000
                              ===============
                              _______________
Total Credits                        871.5000
                              ===============
```