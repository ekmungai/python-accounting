from python_accounting.mixins.trading import TradingMixin
from typing import Any


class SellingMixin(TradingMixin):
    """This class provides validation for transaction's that sell an entity's goods and services"""

    line_item_types: list
    main_account_types: list
    account_type_map: dict

    def __init__(self, **kw: Any) -> None:
        from python_accounting.models import Account

        self.line_item_types: list = [Account.AccountType.OPERATING_REVENUE]

        self.account_type_map: dict = {
            "ClientInvoice": Account.AccountType.RECEIVABLE,
            "CreditNote": Account.AccountType.RECEIVABLE,
            "CashSale": Account.AccountType.BANK,
        }
        super().__init__(**kw)
