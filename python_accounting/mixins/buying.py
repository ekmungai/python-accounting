# mixins/buying.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Provides functionality to Transactions that can purchase goods and services for an Entity.

"""

from typing import Any
from python_accounting.mixins.trading import TradingMixin


# pylint: disable=too-few-public-methods
class BuyingMixin(TradingMixin):
    """
    This class provides validation for Transaction that buy goods and services for an Entity.
    """

    line_item_types: list
    """
    (`list` of `Account.AccountType`): A list of Account
    Types that are allowed as Line Item accounts for buying Transactions.
    """
    main_account_types: list
    """
    (`list` of `Account.AccountType`): A list of Account
    Types that are allowed as main accounts for buying Transactions.
    """
    account_type_map: dict
    """
    (`dict` of `Account.AccountType`): A mapping of
    Transactions to the Account Types that apply to their validation.
    """

    def __init__(self, **kw: Any) -> None:
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Account,
        )

        self.line_item_types: list = Account.purchasables

        self.account_type_map: dict = {
            "SupplierBill": Account.AccountType.PAYABLE,
            "DebitNote": Account.AccountType.PAYABLE,
            "CashPurchase": Account.AccountType.BANK,
        }
        super().__init__(**kw)
