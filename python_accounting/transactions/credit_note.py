from python_accounting.models import Transaction
from python_accounting.mixins import SellingMixin
from typing import Any


class CreditNote(SellingMixin, Transaction):
    """Class for the Credit Note Transaction"""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.CREDIT_NOTE,
    }

    def __init__(self, **kw: Any) -> None:
        from python_accounting.models import Account

        self.main_account_types: list = [
            Account.AccountType.RECEIVABLE,
        ]
        self.credited = True
        self.transaction_type = Transaction.TransactionType.CREDIT_NOTE
        super().__init__(**kw)
