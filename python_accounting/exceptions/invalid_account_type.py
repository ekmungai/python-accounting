from .base import AccountingExeption


class InvalidAccountTypeError(AccountingExeption):
    """The account type must be one of those given in the list"""

    def __init__(self, property, account_types) -> None:
        self.message = f"Property {property} must vbe one of {account_types}"
        super().__init__()
