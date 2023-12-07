from .base import AccountingExeption


class InvalidTaxAccountError(AccountingExeption):
    """A Tax account must be of type Control"""

    message = "A Tax account must be of type Control"
