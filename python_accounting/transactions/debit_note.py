from python_accounting.models import Transaction
from python_accounting.mixins import BuyingMixin
from typing import Any


class DebitNote(BuyingMixin, Transaction):
    """Class for the Debit Note Transaction"""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.DEBIT_NOTE,
    }

    def __init__(self, **kw: Any) -> None:
        from python_accounting.models import Account

        self.main_account_types: list = [
            Account.AccountType.PAYABLE,
        ]
        self.credited = False
        self.transaction_type = Transaction.TransactionType.DEBIT_NOTE
        super().__init__(**kw)
