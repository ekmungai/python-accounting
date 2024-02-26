# reports/balance_sheet.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents the financial position of an Entity.

"""

from datetime import datetime
from strenum import StrEnum
from python_accounting.utils.dates import get_dates
from python_accounting.reports.financial_statement import FinancialStatement

from python_accounting.models import Account


# pylint: disable=too-few-public-methods
class BalanceSheet(FinancialStatement):
    """This class represents Financial Position/Balance Sheet of a given Entity."""

    Accounts = StrEnum(
        "Accounts",
        {
            a.name: a.value
            for a in [
                Account.AccountType.NON_CURRENT_ASSET,
                Account.AccountType.CONTRA_ASSET,
                Account.AccountType.INVENTORY,
                Account.AccountType.BANK,
                Account.AccountType.CURRENT_ASSET,
                Account.AccountType.RECEIVABLE,
                Account.AccountType.NON_CURRENT_LIABILITY,
                Account.AccountType.CONTROL,
                Account.AccountType.CURRENT_LIABILITY,
                Account.AccountType.PAYABLE,
                Account.AccountType.EQUITY,
                Account.AccountType.RECONCILIATION,
            ]
        },
    )
    """(Account.AccountType): The Account types allowed to be in included in the report."""

    config = "balance_sheet"
    """(str): The configuration section for the report."""

    def __init__(self, session, end_date: datetime = None) -> None:
        from python_accounting.reports.income_statement import (  # pylint: disable=import-outside-toplevel
            IncomeStatement,
        )

        self.start_date, self.end_date, _, _ = get_dates(session, None, end_date)
        super().__init__(session)

        self._get_sections(None, self.end_date)

        # Net Assets
        self.result_amounts[self.results.NET_ASSETS.name] = (
            self.totals[self.sections.ASSETS.name]
            - self.totals[self.sections.LIABILITIES.name] * -1
        )

        # Net Profit
        net_profit = IncomeStatement.net_profit(session, self.start_date, self.end_date)
        self.balances["credit"] += net_profit * -1

        # Total Equity
        self.result_amounts[self.results.TOTAL_EQUITY.name] = (
            +self.totals[self.sections.EQUITY.name] * -1 + net_profit
        )

        self.printout = (
            self._print_title(),
            self._print_section(self.sections.ASSETS),
            self._print_total(self.sections.ASSETS),
            self._print_section(self.sections.LIABILITIES, -1),
            self._print_total(self.sections.LIABILITIES, -1),
            self._print_result(self.results.NET_ASSETS, True),
            self._print_section(self.sections.EQUITY, -1),
            self._print_result(self.results.TOTAL_EQUITY, True),
        )

    def __repr__(self) -> str:
        return f"""Assets: {abs(self.totals[self.sections.ASSETS.name])},
         Liabilities: {abs(self.totals[self.sections.LIABILITIES.name])},
         Equity: {abs(self.result_amounts[self.results.TOTAL_EQUITY.name])}"""
