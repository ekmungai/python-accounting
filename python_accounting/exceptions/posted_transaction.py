from .base import AccountingExeption


class PostedTransactionError(AccountingExeption):
    """Changes are not allowed for a posted Transaction"""

    def __init__(self, message) -> None:
        self.message = message
        super().__init__()
