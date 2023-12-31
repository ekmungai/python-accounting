from python_accounting.models import Transaction
from python_accounting.exceptions import (
    MissingMainAccountAmountError,
    UnbalancedTransactionError,
    InvalidTaxChargeError,
)
from typing import Any


class JournalEntry(Transaction):
    """Class for the Journal Entry Transaction"""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.JOURNAL_ENTRY,
    }

    def __init__(self, **kw: Any) -> None:
        self.transaction_type = Transaction.TransactionType.JOURNAL_ENTRY
        super().__init__(**kw)

    def _validate_subclass_line_items(self, line_item):
        if self.compound and line_item.tax_id:
            raise InvalidTaxChargeError(f"Compound {self.__class__.__name__}")
        return line_item

    def get_compound_entries(self) -> tuple:
        """Prepare the compound entries for the Transaction"""

        if not self.compound:
            return {}

        compound_entries = dict(Debit=[], Credit=[])
        compound_entries["Credit" if self.credited else "Debit"].append(
            [self.account_id, self.main_account_amount]
        )

        for line_item in self.line_items:
            compound_entries["Credit" if line_item.credited else "Debit"].append(
                [line_item.account_id, line_item.amount * line_item.quantity]
            )
        return compound_entries["Debit"], compound_entries["Credit"]

    def validate(self, session) -> None:
        """Validate the buying Transaction properties"""

        if self.compound:
            if not self.main_account_amount:
                raise MissingMainAccountAmountError

            debits, credits = self.get_compound_entries()

            if (
                sum([d[1] for d in debits]) != sum([c[1] for c in credits])
                and len(self.line_items) > 0
            ):
                raise UnbalancedTransactionError

        super().validate(session)
