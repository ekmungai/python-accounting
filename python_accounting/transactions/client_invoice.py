from python_accounting.models import Transaction
from python_accounting.mixins import SellingMixin, ClearingMixin
from typing import Any


class ClientInvoice(SellingMixin, ClearingMixin, Transaction):
    """Class for the Client Invoice Transaction"""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.CLIENT_INVOICE,
    }

    def __init__(self, **kw: Any) -> None:
        self.credited = False
        self.transaction_type = Transaction.TransactionType.CLIENT_INVOICE
        super().__init__(**kw)
