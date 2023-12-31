from .base import AccountingExeption


class MissingMainAccountAmountError(AccountingExeption):
    """A Compound Journal Entry Transaction must have a main account amount"""

    message = "A Compound Journal Entry Transaction must have a main account amount"
