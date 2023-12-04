from .base import AccountingExeption


class DuplicateReportingPeriodError(AccountingExeption):
    """An Entity can only have one reporting period per calendar year"""

    message = "A reporting Period already exists for that calendar year"
