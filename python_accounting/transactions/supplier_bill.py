from python_accounting.models import Transaction
from python_accounting.mixins import BuyingMixin
from typing import Any


class SupplierBill(BuyingMixin, Transaction):
    """Class for the Supplier Bill Transaction"""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.SUPPLIER_BILL,
    }

    def __init__(self, **kw: Any) -> None:
        from python_accounting.models import Account

        self.main_account_types: list = [
            Account.AccountType.PAYABLE,
        ]
        self.credited = True
        self.transaction_type = Transaction.TransactionType.SUPPLIER_BILL
        super().__init__(**kw)
