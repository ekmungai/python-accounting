from python_accounting.models import Transaction
from python_accounting.mixins.trading import TradingMixin
from python_accounting.mixins import AssigningMixin
from typing import Any


class SupplierPayment(TradingMixin, AssigningMixin, Transaction):
    """Class for the Supplier Payment Transaction"""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.SUPPLIER_PAYMENT,
    }

    def __init__(self, **kw: Any) -> None:
        from python_accounting.models import Account

        self.line_item_types: list = [Account.AccountType.BANK]
        self.main_account_types: list = [Account.AccountType.PAYABLE]
        self.account_type_map: dict = {
            "SupplierPayment": Account.AccountType.PAYABLE,
        }

        self.credited = False
        self.transaction_type = Transaction.TransactionType.SUPPLIER_PAYMENT
        super().__init__(**kw)
