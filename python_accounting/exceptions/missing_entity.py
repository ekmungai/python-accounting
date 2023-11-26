from .base import AccountingExeption


class MissingEntityError(AccountingExeption):
    """Accounting objects must all be associated with an Entity"""

    message = "Accounting objects must have an Entity"
