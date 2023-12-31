from .base import AccountingExeption


class UnbalancedTransactionError(AccountingExeption):
    """Total Debit amounts do not match total Credit amounts"""

    message = "Total Debit amounts do not match total Credit amounts"
