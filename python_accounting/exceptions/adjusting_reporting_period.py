from .base import AccountingExeption


class AdjustingReportingPeriodError(AccountingExeption):
    """Only Journal Entry Transactions can be recorded for adjusting status reporting periods"""

    def __init__(self, reporting_period) -> None:
        self.message = f"Only Journal Entry Transactions can be recorded for Reporting Period: {reporting_period} which has the Adjusting Status"
        super().__init__()
