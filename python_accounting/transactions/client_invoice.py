# transactions/client_invoice.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Client Invoice Transaction.

"""

from typing import Any
from python_accounting.models import Transaction
from python_accounting.mixins import SellingMixin, ClearingMixin


class ClientInvoice(  # pylint: disable=too-many-ancestors
    SellingMixin, ClearingMixin, Transaction
):
    """Class for the Client Invoice Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.CLIENT_INVOICE,
    }

    def __init__(self, **kw: Any) -> None:
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Account,
        )

        self.main_account_types: list = [
            Account.AccountType.RECEIVABLE,
        ]
        self.credited = False
        self.transaction_type = Transaction.TransactionType.CLIENT_INVOICE
        super().__init__(**kw)
