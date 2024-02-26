# transactions/client_receipt.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Client Receipt Transaction.

"""

from typing import Any
from python_accounting.models import Transaction
from python_accounting.mixins import AssigningMixin
from python_accounting.mixins.trading import TradingMixin


class ClientReceipt(  # pylint: disable=too-many-ancestors
    TradingMixin, AssigningMixin, Transaction
):
    """Class for the Client Receipt Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.CLIENT_RECEIPT,
    }

    def __init__(self, **kw: Any) -> None:
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Account,
        )

        self.line_item_types: list = [Account.AccountType.BANK]
        self.main_account_types: list = [Account.AccountType.RECEIVABLE]
        self.account_type_map: dict = {
            "ClientReceipt": Account.AccountType.RECEIVABLE,
        }

        self.credited = True
        self.transaction_type = Transaction.TransactionType.CLIENT_RECEIPT
        super().__init__(**kw)
