from .base import AccountingExeption


class InvalidTransactionDateError(AccountingExeption):
    """The Transaction date cannot be the exact beginning of the reporting period"""

    message = "The Transaction date cannot be at the exact beginning of the Reporting Period. Use a Balance object instead"
