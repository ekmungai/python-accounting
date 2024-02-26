# mixins/trading.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Provides functionality to Transactions that can by and sell goods and services for an Entity.

"""
from python_accounting.exceptions import (
    InvalidMainAccountError,
    InvalidLineItemAccountError,
    InvalidTaxChargeError,
)


# pylint: disable=too-few-public-methods
class TradingMixin:
    """
    This class provides validation for transactions that trade goods and services
    for an entity.
    """

    def _validate_subclass_line_items(self, line_item):
        if line_item.account.account_type not in self.line_item_types:
            raise InvalidLineItemAccountError(
                self.__class__.__name__,
                [t.value for t in self.line_item_types],
            )
        if getattr(self, "no_tax", False) and line_item.tax_id:
            raise InvalidTaxChargeError(self.__class__.__name__)
        return line_item

    def validate(self, session) -> None:
        """
        Validates the trading Transaction properties.

        Args:
            session (Session): The accounting session to which the Transaction belongs.

        Returns:
            None
        """

        account = self._get_main_account(session)

        if account.account_type not in self.main_account_types:
            raise InvalidMainAccountError(
                self.__class__.__name__,
                self.account_type_map[self.__class__.__name__],
            )
        super().validate(session)
