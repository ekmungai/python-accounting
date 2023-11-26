from .base import AccountingExeption


class LastEntityError(AccountingExeption):
    """The Last Entity should not be deleted"""

    message = "Cannot delete the last Entity"
