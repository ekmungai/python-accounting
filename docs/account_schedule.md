## Account Schedule
Account Schedules are similar to statements in that the present chronological records of transactions that have been posted to an account, the difference being that only transactions with outstanding balances, i.e. those that have not been cleared completely are displayed. Schedules can only be created for Account::RECEIVABLE and Account::PAYABLE account types.

**Parameters**: The same as [Account Statements](statements.md), but with the additional boolean `schedule = True`.


**Returns** A dictionary with:
- transactions (list): Outstanding clearable Transactions posted to the Account as at the end date.
- total_amount (Decimal): The total amount of the Transactions in the Schdeule.
- cleared_amount (Decimal): The amount of the Transactions in the Schdeule that has been cleared.
- uncleared_amount (Decimal): The amount of the Transactions in the Schdeule that is still outstanding.

Apart from their standard attributes, the Transactions returned also include a `cleared_amount` property which indicates how much of the Transaction has been offset by assignable Transactions, an `uncleared_amount` property which shows the balance yet to be offset and an `age` property which shows in days how long the Transaction has been outstanding.
 
**Example**
```python
account = session.get(Account, account.id)

statement = account.statement(session, None, None, True)

print(statement)

{
    'transactions': [...], 
    'total_amount': Decimal('0'), 
    'cleared_amount': Decimal('0'), 
    'uncleared_amount': Decimal('0')
}
```