# reports/trial_balance.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents the equality of all the credit and debit balances of an Entity.

"""

from datetime import datetime
from python_accounting.reports.financial_statement import FinancialStatement
from python_accounting.utils.dates import get_dates


# pylint: disable=too-few-public-methods
class TrialBalance(FinancialStatement):
    # pylint: disable=line-too-long
    """This class represents all the balances of the chart of accounts, compared against each other."""

    config = "trial_balance"
    """(str): The configuration section for the report."""

    def __init__(self, session, end_date: datetime = None) -> None:
        self.start_date, self.end_date, _, _ = get_dates(session, None, end_date)
        super().__init__(session)

        self._get_sections(None, self.end_date)

        # Debits
        self.result_amounts[self.results.DEBIT.name] = self.balances["debit"]

        # Credits
        self.result_amounts[self.results.CREDIT.name] = abs(self.balances["credit"])

        self.printout = (
            self._print_title(),
            self._print_section(self.sections.INCOME_STATEMENT),
            self._print_total(self.sections.INCOME_STATEMENT),
            self._print_section(self.sections.BALANCE_SHEET),
            self._print_total(self.sections.BALANCE_SHEET),
            self._print_result(self.results.DEBIT, True),
            self._print_result(self.results.CREDIT, True),
        )
