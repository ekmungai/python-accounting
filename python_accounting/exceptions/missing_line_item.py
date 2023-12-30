from .base import AccountingExeption


class MissingLineItemError(AccountingExeption):
    """A Transaction must have at least one Line Item to be posted"""

    message = "A Transaction must have at least one Line Item to be posted"
