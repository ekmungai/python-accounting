from .base import AccountingExeption


class RedundantTransactionError(AccountingExeption):
    """A Transaction main account cannot be used as the account for any of its Line Items"""

    def __init__(self, line_item) -> None:
        self.message = (
            f"Line Item <{line_item}> Account is the same as the Transaction Account"
        )
        super().__init__()
