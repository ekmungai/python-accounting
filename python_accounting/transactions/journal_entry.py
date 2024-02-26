# transactions/journal_entry.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
This is the most powerful Transaction in the entire system, capable of 
    directly accessing the ledger.

"""
from typing import Any
from python_accounting.models import Transaction
from python_accounting.mixins import AssigningMixin, ClearingMixin
from python_accounting.exceptions import (
    MissingMainAccountAmountError,
    UnbalancedTransactionError,
    InvalidTaxChargeError,
)


class JournalEntry(  # pylint: disable=too-many-ancestors
    Transaction, AssigningMixin, ClearingMixin
):
    """Class for the Journal Entry Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.JOURNAL_ENTRY,
    }

    def __init__(self, **kw: Any) -> None:
        self.transaction_type = Transaction.TransactionType.JOURNAL_ENTRY
        self.credited = True
        super().__init__(**kw)

    def _validate_subclass_line_items(self, line_item):
        if self.compound and line_item.tax_id:
            raise InvalidTaxChargeError(f"Compound {self.__class__.__name__}")

    def get_compound_entries(self) -> tuple:
        """
        Prepare the compound entries for the Transaction

        Returns:
            tuple: A tuple of debited, credited Line Items
        """

        if not self.compound:
            return (0, 0)

        compound_entries = {"Debit": [], "Credit": []}
        compound_entries["Credit" if self.credited else "Debit"].append(
            [self.account_id, self.main_account_amount]
        )

        for line_item in self.line_items:
            compound_entries["Credit" if line_item.credited else "Debit"].append(
                [line_item.account_id, line_item.amount * line_item.quantity]
            )
        return compound_entries["Debit"], compound_entries["Credit"]

    def validate(self, session) -> None:
        """
        Validates the Journal Entry properties

        Args:
            session (Session): The accounting session to which the Journal Entry belongs.

        Raises:
            UnbalancedTransactionError: If the debit amounts do not equal the credit amounts.

        Returns:
            None

        """

        if self.compound:
            if not self.main_account_amount:
                raise MissingMainAccountAmountError

            debit_amounts, credit_amounts = self.get_compound_entries()

            if (
                sum(d[1] for d in debit_amounts) != sum(c[1] for c in credit_amounts)
                and len(self.line_items) > 0
            ):
                raise UnbalancedTransactionError

        super().validate(session)
