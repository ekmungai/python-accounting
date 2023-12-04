from .base import AccountingExeption


class InvalidCategoryAccountTypeError(AccountingExeption):
    """The account type must the same as the category account type"""

    def __init__(self, account_type, category_account_type) -> None:
        self.message = (
            f"Cannot assign {account_type} Account to {category_account_type} Category"
        )
        super().__init__()
