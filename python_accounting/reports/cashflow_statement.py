# reports/cashflow_statement.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents the movement of liquid funds of an Entity.

"""
from datetime import datetime
from python_accounting.reports.financial_statement import FinancialStatement
from python_accounting.config import config
from python_accounting.utils.dates import get_dates
from python_accounting.models import Account


# pylint: disable=too-few-public-methods
class CashflowStatement(FinancialStatement):
    # pylint: disable=line-too-long
    """This class represents the movement of balances of Balance Sheet accounts during the given period."""

    config = "cashflow_statement"
    """config (str): The configuration section for the report."""

    sub_sections: dict
    """sub_sections (dict): The categories of the contents of the sections of the report."""

    # pylint: enable=line-too-long
    def __init__(
        self, session, start_date: datetime = None, end_date: datetime = None
    ) -> None:
        self.start_date, self.end_date, _, _ = get_dates(session, start_date, end_date)
        super().__init__(session)

        self.sub_sections = {
            k: v["sub_sections"]
            for k, v in config.reports[self.config]["sections"].items()
        }

        self._get_sections(self.start_date, self.end_date, False)

        cash_balances = Account.section_balances(
            self.session,
            [Account.AccountType.BANK],
            start_date,
            end_date,
            True,
        )

        # Beginning cash balance
        self.balances["NET_CASH_FLOW"]["Beginning Cash Balance"] = cash_balances[
            "opening"
        ]

        # Net Cash Flow
        self.balances["NET_CASH_FLOW"]["Net Cash Flow"] = self.totals[
            "NET_CASH_FLOW"
        ] = sum(v for v in self.totals.values())

        # Ending Cash Balance
        self.result_amounts[self.results.END_CASH_BALANCE.name] = (
            self.balances["NET_CASH_FLOW"]["Beginning Cash Balance"]
            + self.balances["NET_CASH_FLOW"]["Net Cash Flow"]
        )

        # Cashbook Balance
        self.result_amounts[self.results.CASHBOOK_BALANCE.name] = cash_balances[
            "closing"
        ]
        self.printout = (
            self._print_title(),
            self._print_section(self.sections.OPERATING_CASH_FLOW),
            self._print_total(self.sections.OPERATING_CASH_FLOW),
            self._print_section(self.sections.INVESTMENT_CASH_FLOW),
            self._print_total(self.sections.INVESTMENT_CASH_FLOW),
            self._print_section(self.sections.FINANCING_CASH_FLOW),
            self._print_total(self.sections.FINANCING_CASH_FLOW),
            self._print_section(self.sections.NET_CASH_FLOW),
            self._print_result(self.results.END_CASH_BALANCE, True),
            self._print_result(self.results.CASHBOOK_BALANCE, True),
        )

    def __repr__(self) -> str:
        return f"""Operating: {self.totals[self.sections.OPERATING_CASH_FLOW.name]},
         Investing: {self.totals[self.sections.INVESTMENT_CASH_FLOW.name]},
         Financing: {self.totals[self.sections.FINANCING_CASH_FLOW.name]},
         Net: {self.totals[self.sections.NET_CASH_FLOW.name]}"""

    def _get_sections(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        full_balance: bool = True,
    ) -> None:
        for section, sub_sections in self.sub_sections.items():
            for sub_section in sub_sections:
                label, account_types = config.reports[self.config]["sub_sections"][
                    sub_section
                ].items()
                balances = Account.section_balances(
                    self.session,
                    account_types[1],
                    start_date,
                    end_date,
                    full_balance,
                )
                if balances["movement"] != 0:
                    self.balances[section][label[1]] = balances["movement"]
                    self.totals[section] += balances["movement"]

    def _print_section(self, section, factor=1) -> str:
        content = f"\n{section.value}"
        for sub_section, total in self.balances[section.name].items():
            label = f"\n{self.indent}{sub_section}"
            content += f"{label}{total * factor:>{self.width - len(label) + 1}}"
        return content
