from .base import AccountingExeption


class InvalidTaxChargeError(AccountingExeption):
    """A Contra Entry Transaction cannot be charged Tax"""

    message = "A Contra Entry Transaction cannot be charged Tax"
