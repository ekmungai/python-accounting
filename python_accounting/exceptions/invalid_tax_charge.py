from .base import AccountingExeption


class InvalidTaxChargeError(AccountingExeption):
    """A Contra Entry Transaction cannot be charged Tax"""

    def __init__(self, classname) -> None:
        self.message = f"{classname} Transactions cannot be charged Tax"
        super().__init__()
