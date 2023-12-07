from .base import AccountingExeption


class MultipleOpenPeriodsError(AccountingExeption):
    """An Entity can only have one reporting period open at a time"""

    message = "There can only be one Open Reporting Period per Entity at a time"
