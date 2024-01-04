from python_accounting.mixins.trading import TradingMixin
from typing import Any


class BuyingMixin(TradingMixin):
    """This class provides validation for transaction's that buy goods and services for an entity's"""

    line_item_types: list
    main_account_types: list
    account_type_map: dict

    def __init__(self, **kw: Any) -> None:
        from python_accounting.models import Account

        self.line_item_types: list = Account.purchasables

        self.account_type_map: dict = {
            "SupplierBill": Account.AccountType.PAYABLE,
            "DebitNote": Account.AccountType.PAYABLE,
            "CashPurchase": Account.AccountType.BANK,
        }
        super().__init__(**kw)
