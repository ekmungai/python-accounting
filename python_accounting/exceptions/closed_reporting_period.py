from .base import AccountingExeption


class ClosedReportingPeriodError(AccountingExeption):
    """Transactions cannot be recorded for closed reporting periods"""

    def __init__(self, reporting_period) -> None:
        self.message = f"Transaction cannot be recorded because Reporting Period: {reporting_period} is Closed"
        super().__init__()
