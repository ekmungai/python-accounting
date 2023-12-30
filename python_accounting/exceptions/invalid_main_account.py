from .base import AccountingExeption


class InvalidMainAccountError(AccountingExeption):
    """The account type of the transaction must be of the type given"""

    def __init__(self, classname, account_type: list) -> None:
        self.message = f"{classname} Transaction main Account be of type {account_type}"
        super().__init__()
