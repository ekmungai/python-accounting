from strenum import StrEnum
from datetime import datetime
from python_accounting.config import config
from python_accounting.utils.dates import get_dates
from python_accounting.reports.financial_statement import FinancialStatement
from python_accounting.models import Account


class BalanceSheet(FinancialStatement):
    """This class represents the Statement of Financial Position/Balance Sheet of a given Entity"""

    BalanceSheetAccounts = StrEnum(
        "BalanceSheetAccounts",
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

    # Income Statement Sections
    Sections = StrEnum(
        "Sections",
        {k: v["label"] for k, v in config.reports["balance_sheet"]["sections"].items()},
    )

    # Income Statement Results
    Results = StrEnum(
        "Results",
        {k: v for k, v in config.reports["balance_sheet"]["results"].items()},
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
        _, self.end_date, _, _ = get_dates(session, start_date, end_date)
        self.title = config.reports["BALANCE_SHEET"]
        super().__init__(session)

        self._get_sections(None, self.end_date)

        # net assets
        self.results[BalanceSheet.Results.NET_ASSETS.name] = (
            self.totals[BalanceSheet.Sections.ASSETS.name]
            - self.totals[BalanceSheet.Sections.LIABILITIES.name]
        )

        # Total Equity
        self.results[BalanceSheet.Results.TOTAL_EQUITY.name] = (
            self.totals[BalanceSheet.Sections.RECONCILIATION.name]
            + self.totals[BalanceSheet.Sections.EQUITY.name]
        )

        self.printout = (
            self._print_title(),
            self._print_section(BalanceSheet.Sections.ASSETS),
            self._print_total(BalanceSheet.Sections.ASSETS),
            self._print_section(BalanceSheet.Sections.LIABILITIES, -1),
            self._print_total(BalanceSheet.Sections.LIABILITIES, -1),
            self._print_result(BalanceSheet.Results.NET_ASSETS, True),
            self._print_section(BalanceSheet.Sections.RECONCILIATION),
            self._print_section(BalanceSheet.Sections.EQUITY, -1),
            self._print_result(BalanceSheet.Results.TOTAL_EQUITY, True),
        )
