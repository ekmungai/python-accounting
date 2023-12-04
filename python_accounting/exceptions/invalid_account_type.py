from .base import AccountingExeption


class InvalidAccountTypeError(AccountingExeption):
    """The account type must be one of those given in the list"""

    def __init__(self, property, account_types: list) -> None:
        self.message = f"Property {property} must be one of {account_types}"
        super().__init__()
