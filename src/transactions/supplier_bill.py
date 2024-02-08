# transactions/supplier_bill.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Supplier Bill Transaction.

"""
from typing import Any
from src.models import Transaction
from src.mixins import BuyingMixin, ClearingMixin


class SupplierBill(BuyingMixin, ClearingMixin, Transaction):
    """Class for the Supplier Bill Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.SUPPLIER_BILL,
    }

    def __init__(self, **kw: Any) -> None:
        from src.models import (  # pylint: disable=import-outside-toplevel
            Account,
        )

        self.main_account_types: list = [
            Account.AccountType.PAYABLE,
        ]
        self.credited = True
        self.transaction_type = Transaction.TransactionType.SUPPLIER_BILL
        super().__init__(**kw)
