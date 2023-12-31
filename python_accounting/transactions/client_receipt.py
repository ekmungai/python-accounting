from python_accounting.models import Transaction
from python_accounting.mixins.trading import TradingMixin
from typing import Any


class ClientReceipt(TradingMixin, Transaction):
    """Class for the Client Receipt Transaction"""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.CLIENT_RECEIPT,
    }

    def __init__(self, **kw: Any) -> None:
        from python_accounting.models import Account

        self.line_item_types: list = [Account.AccountType.BANK]
        self.main_account_types: list = [Account.AccountType.RECEIVABLE]
        self.account_type_map: dict = {
            "ClientReceipt": Account.AccountType.RECEIVABLE,
        }

        self.credited = True
        self.transaction_type = Transaction.TransactionType.CLIENT_RECEIPT
        super().__init__(**kw)
