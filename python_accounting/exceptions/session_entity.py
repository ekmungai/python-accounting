from .base import AccountingExeption


class SessionEntityError(AccountingExeption):
    """The Session Entity should not be deleted"""

    message = "Cannot delete the session Entity"
