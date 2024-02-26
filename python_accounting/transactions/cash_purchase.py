# transactions/cash_purchase.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Cash Purchase Transaction.

"""

from typing import Any
from python_accounting.models import Transaction
from python_accounting.mixins import BuyingMixin


class CashPurchase(BuyingMixin, Transaction):  # pylint: disable=too-many-ancestors
    """Class for the Cash Purchase Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.CASH_PURCHASE,
    }

    def __init__(self, **kw: Any) -> None:
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Account,
        )

        self.main_account_types: list = [
            Account.AccountType.BANK,
        ]
        self.credited = True
        self.transaction_type = Transaction.TransactionType.CASH_PURCHASE
        super().__init__(**kw)
