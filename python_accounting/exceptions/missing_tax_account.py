from .base import AccountingExeption


class MissingTaxAccountError(AccountingExeption):
    """A non Zero Rate Tax must have an associated control account"""

    message = "A non Zero Rate Tax must have an associated Control Account"
