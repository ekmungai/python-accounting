from .base import AccountingExeption


class InvalidBalanceDateError(AccountingExeption):
    """Unless the Entity allows for mid year balances, the balance date must be earlier than its reporting period's start"""

    message = "Transaction date must be earlier than the first day of the Balance's Reporting Period"
