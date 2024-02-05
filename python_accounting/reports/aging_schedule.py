# reports/aging_schedule.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents amounts oustanding to/from suppliers/clients, grouped by their age.

"""

from datetime import datetime
from python_accounting.models import Account
from python_accounting.config import config
from python_accounting.utils.dates import get_dates


class AgingSchedule:
    """
    This class displays the outstanding balances for recievables and payables categorised
        by how long they have been outstanding.

    Attributes:
        brackets (dict): Categories of ages in days and their labels.
        balances (str): The total outstanding amounts per age bracket.
        accounts (list): The Account who's outsanding transactions constitue the balances.
        account_type (Account.AccountType.RECEIVABLE|Account.AccountType.RECEIVABLE):
            The Account type to get aged balances for. Can only be Receivable or Payable.
        end_date (datetime): The latest transaction date for Transaction amounts to be included
                in the balances.
    """

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
        return f"{self.account_type} Aging Schedule as at {str(self.end_date)}"

    def _allocate_balances(self, transactions: list, account: Account) -> None:
        for transaction in transactions:
            bracket = [
                bracket
                for bracket, max_age in self.brackets.items()
                if transaction.age <= max_age
            ][0]
            self.balances[bracket] += transaction.uncleared_amount
            account.balances[bracket] += transaction.uncleared_amount
