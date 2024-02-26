# transactions/supplier_payment.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Supplier Payment Transaction.

"""
from typing import Any
from python_accounting.models import Transaction
from python_accounting.mixins.trading import TradingMixin
from python_accounting.mixins import AssigningMixin


class SupplierPayment(
    # pylint: disable=too-many-ancestors
    TradingMixin,
    AssigningMixin,
    Transaction,
):
    """Class for the Supplier Payment Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.SUPPLIER_PAYMENT,
    }

    def __init__(self, **kw: Any) -> None:
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Account,
        )

        self.line_item_types: list = [Account.AccountType.BANK]
        self.main_account_types: list = [Account.AccountType.PAYABLE]
        self.account_type_map: dict = {
            "SupplierPayment": Account.AccountType.PAYABLE,
        }

        self.credited = False
        self.transaction_type = Transaction.TransactionType.SUPPLIER_PAYMENT
        super().__init__(**kw)
