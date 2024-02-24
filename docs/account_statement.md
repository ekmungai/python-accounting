## Account Statement
Account Statements are chronological records of transactions that have been posted to an account and their effects on its balance. Statements can be created for all accounts in the chart.

**Parameters**:
- session (Session): The accounting session to which the Account belongs.
- start_date (datetime): The earliest transaction date for Transaction amounts to be included in the statement.
- end_date (datetime): The latest transaction date for Transaction amounts to be included in the statement.


**Returns** A dictionary with:
- opening_balance (Decimal): The balance of the Account at the beginning of the statement period.
- transactions (list): Transactions posted to the Account during the period.
- closing_balance (Decimal): The balance of the Account at the end of the statement period.

Apart from their standard attributes, the Transactions returned also include a `debit` and `credit` property which indicates the the amount added or subtracted to/from the account respectively. There's also a `balance` property which keeps a running balance starting from the opening balance and adding the debits and credits of the transactions and ending with the closing balance.
 
**Example**
```python
account = session.get(Account, account.id)

statement = account.statement(session)

print(statement)

{
    'opening_balance': Decimal('0'), 
    'transactions': [...], 
    'closing_balance': Decimal('0')
}
```