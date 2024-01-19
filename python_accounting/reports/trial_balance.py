from datetime import datetime
from python_accounting.reports.financial_statement import FinancialStatement
from python_accounting.config import config
from python_accounting.utils.dates import get_dates
from python_accounting.models import Account


class TrialBalance(FinancialStatement):
    """This class represents all the balances of the chart of accounts, compared against each other"""

    config = "trial_balance"

    def __init__(self, session, end_date: datetime = None) -> None:
        from python_accounting.reports import IncomeStatement, BalanceSheet

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
