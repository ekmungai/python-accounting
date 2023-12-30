from .base import AccountingExeption


class InvalidLineItemAccountError(AccountingExeption):
    """The Line Item main Account type must be one of those given in the list"""

    def __init__(self, classname, account_types: list) -> None:
        self.message = f"{classname} Transaction Line Item Account type be one of: {', '.join(account_types)}"
        super().__init__()
