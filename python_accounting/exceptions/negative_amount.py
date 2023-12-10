from .base import AccountingExeption


class NegativeAmountError(AccountingExeption):
    """Accounting amounts should not be negative"""

    def __init__(self, amount_class, property="amount") -> None:
        self.message = f"{amount_class} {property} cannot be negative"
        super().__init__()
