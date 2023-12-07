from .base import AccountingExeption


class InvalidBalanceTransactionError(AccountingExeption):
    """Balance Transaction must be one of Client Invoice, Supplier Bill or Journal Entry"""

    message = "Balance Transaction must be one of Client Invoice, Supplier Bill or Journal Entry"
