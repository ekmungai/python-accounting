from python_accounting.models import Transaction
from python_accounting.mixins import SellingMixin
from typing import Any


class CashSale(SellingMixin, Transaction):
    """Class for the Cash Sale Transaction"""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.CASH_SALE,
    }

    def __init__(self, **kw: Any) -> None:
        from python_accounting.models import Account

        self.main_account_types: list = [
            Account.AccountType.BANK,
        ]
        self.credited = False
        self.transaction_type = Transaction.TransactionType.CASH_SALE
        super().__init__(**kw)
