from datetime import datetime
from python_accounting.models import Account
from python_accounting.config import config
from python_accounting.utils.dates import get_dates


class AgingSchedule:
    """This class displays the outstanding balances for recievables and payables categorised by how long they have been outstanding"""

    brackets = config.reports["aging_schedule_brackets"]
    balances: dict
    accounts: list
    account_type = None
    end_date: datetime

    def __init__(
        self,
        session,
        account_type: Account.AccountType,
        end_date: datetime = None,
    ) -> None:
        self.account_type = account_type
        self.accounts = []
        self.balances = {k: 0 for k, v in self.brackets.items()}
        _, end_date, _, _ = get_dates(session, None, end_date)

        for account, transactions in [
            (
                account,
                account.statement(session, None, end_date, True)["transactions"],
            )
            for account in session.query(Account)
            .filter(Account.account_type == account_type)
            .filter(Account.entity_id == session.entity.id)
            .all()
        ]:
            if transactions:
                account.balances = {k: 0 for k, v in self.brackets.items()}
                self._allocate_balances(transactions, account)
                self.accounts.append(account)

    def __repr__(self) -> str:
        return f"{self.account_type} Aging Schedule as at {str(self.period)}"

    def _allocate_balances(self, transactions: list, account: Account) -> None:
        """Allocate the uncleared balance of each transaction to its appropriate age bracket"""
        for transaction in transactions:
            bracket = [
                bracket
                for bracket, max_age in self.brackets.items()
                if transaction.age <= max_age
            ][0]
            self.balances[bracket] += transaction.uncleared_amount
            account.balances[bracket] += transaction.uncleared_amount
