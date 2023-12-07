from .base import AccountingExeption


class InvalidBalanceAccountError(AccountingExeption):
    """Income Statement Accounts cannot have an opening balance"""

    message = "Income Statement Accounts cannot have an opening balance"
