from strenum import StrEnum
from datetime import datetime
from python_accounting.config import config
from python_accounting.models import Account
from python_accounting.reports.financial_statement import FinancialStatement
from python_accounting.utils.dates import get_dates


class IncomeStatement(FinancialStatement):
    """This class represents the Income Statement/Profit and Loss of a given Entity"""

    name: str = "INCOME_STATEMENT"
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

    # Income Statement Sections
    Sections = StrEnum(
        "Sections",
        {
            k: v["label"]
            for k, v in config.reports["income_statement"]["sections"].items()
        },
    )

    # Income Statement Results
    Results = StrEnum(
        "Results",
        {k: v for k, v in config.reports["income_statement"]["results"].items()},
    )

    title: str
    sections = [section.name for section in Sections]
    accounts = {k: {} for k in sections}
    balances = {k: {} for k in sections}
    totals = {k: 0 for k in sections}
    results = {}

    def __init__(
        self, session, start_date: datetime = None, end_date: datetime = None
    ) -> None:
        self.start_date, self.end_date, _, _ = get_dates(session, start_date, end_date)
        self.title = config.reports[self.name]["title"]
        self.config = config.reports[self.name]["config"]
        super().__init__(session)

        self._get_sections(self.start_date, self.end_date, False)

        # gross profit
        self.results[IncomeStatement.Results.GROSS_PROFIT.name] = (
            self.totals[IncomeStatement.Sections.OPERATING_REVENUES.name]
            + self.totals[IncomeStatement.Sections.OPERATING_EXPENSES.name]
        ) * -1

        # total revenue
        self.results[IncomeStatement.Results.TOTAL_REVENUE.name] = (
            self.results[IncomeStatement.Results.GROSS_PROFIT.name]
            + self.totals[IncomeStatement.Sections.NON_OPERATING_REVENUES.name] * -1
        )

        # total expenses
        self.results[IncomeStatement.Results.TOTAL_EXPENSES.name] = self.totals[
            IncomeStatement.Sections.NON_OPERATING_EXPENSES.name
        ]

        # net profit
        self.results[IncomeStatement.Results.NET_PROFIT.name] = (
            self.results[IncomeStatement.Results.TOTAL_REVENUE.name]
            - self.totals[IncomeStatement.Sections.NON_OPERATING_EXPENSES.name]
        )

        self.printout = (
            self._print_title(),
            self._print_section(IncomeStatement.Sections.OPERATING_REVENUES, -1),
            self._print_section(IncomeStatement.Sections.OPERATING_EXPENSES),
            self._print_result(IncomeStatement.Results.GROSS_PROFIT),
            self._print_section(IncomeStatement.Sections.NON_OPERATING_REVENUES, -1),
            self._print_result(IncomeStatement.Results.TOTAL_REVENUE),
            self._print_section(IncomeStatement.Sections.NON_OPERATING_EXPENSES),
            self._print_result(IncomeStatement.Results.TOTAL_EXPENSES),
            self._print_result(IncomeStatement.Results.NET_PROFIT, True),
        )

    def __repr__(self) -> str:
        return "Revenue: {}, Gross Profit: {}, Net Profit: {}".format(
            self.results[IncomeStatement.Results.TOTAL_REVENUE.name],
            self.results[IncomeStatement.Results.GROSS_PROFIT.name],
            self.results[IncomeStatement.Results.NET_PROFIT.name],
        )
