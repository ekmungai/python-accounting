from strenum import StrEnum
from decimal import Decimal
from datetime import datetime
from python_accounting.config import config
from python_accounting.models import Account
from python_accounting.reports.financial_statement import FinancialStatement
from python_accounting.utils.dates import get_dates


class IncomeStatement(FinancialStatement):
    """This class represents the Income Statement/Profit and Loss of a given Entity"""

    config = "income_statement"
    Accounts = StrEnum(
        "Accounts",
        {
            a.name: a.value
            for a in [
                Account.AccountType.OPERATING_REVENUE,
                Account.AccountType.NON_OPERATING_REVENUE,
                Account.AccountType.OPERATING_EXPENSE,
                Account.AccountType.DIRECT_EXPENSE,
                Account.AccountType.OVERHEAD_EXPENSE,
                Account.AccountType.OTHER_EXPENSE,
            ]
        },
    )

    def __init__(
        self, session, start_date: datetime = None, end_date: datetime = None
    ) -> None:
        self.start_date, self.end_date, _, _ = get_dates(session, start_date, end_date)
        super().__init__(session)

        self._get_sections(self.start_date, self.end_date, False)

        # gross profit
        self.result_amounts[self.results.GROSS_PROFIT.name] = (
            self.totals[self.sections.OPERATING_REVENUES.name]
            + self.totals[self.sections.OPERATING_EXPENSES.name]
        ) * -1

        # total revenue
        self.result_amounts[self.results.TOTAL_REVENUE.name] = (
            self.result_amounts[self.results.GROSS_PROFIT.name]
            + self.totals[self.sections.NON_OPERATING_REVENUES.name] * -1
        )

        # total expenses
        self.result_amounts[self.results.TOTAL_EXPENSES.name] = self.totals[
            self.sections.NON_OPERATING_EXPENSES.name
        ]

        # net profit
        self.result_amounts[self.results.NET_PROFIT.name] = (
            self.result_amounts[self.results.TOTAL_REVENUE.name]
            - self.totals[self.sections.NON_OPERATING_EXPENSES.name]
        )

        self.printout = (
            self._print_title(),
            self._print_section(self.sections.OPERATING_REVENUES, -1),
            self._print_section(self.sections.OPERATING_EXPENSES),
            self._print_result(self.results.GROSS_PROFIT),
            self._print_section(self.sections.NON_OPERATING_REVENUES, -1),
            self._print_result(self.results.TOTAL_REVENUE),
            self._print_section(self.sections.NON_OPERATING_EXPENSES),
            self._print_result(self.results.TOTAL_EXPENSES),
            self._print_result(self.results.NET_PROFIT, True),
        )

    def __repr__(self) -> str:
        return "Revenue: {}, Gross Profit: {}, Net Profit: {}".format(
            self.result_amounts[self.results.TOTAL_REVENUE.name],
            self.result_amounts[self.results.GROSS_PROFIT.name],
            self.result_amounts[self.results.NET_PROFIT.name],
        )

    @staticmethod
    def net_profit(
        session, start_date: datetime = None, end_date: datetime = None
    ) -> Decimal:
        """Get the value of net profit for the given period"""
        return (
            Account.section_balances(
                session,
                IncomeStatement.Accounts,
                start_date,
                end_date,
                True,
            )["closing"]
            * -1
        )
