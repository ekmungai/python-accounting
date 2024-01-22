import importlib
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, select, func
from sqlalchemy.types import DECIMAL
from datetime import datetime
from python_accounting.mixins import IsolatingMixin
from python_accounting.models import Balance, Transaction
from python_accounting.config import config
from python_accounting.exceptions import (
    UnassignableTransactionError,
    UnclearableTransactionError,
    NegativeAmountError,
    SelfClearanceError,
    UnpostedAssignmentError,
    InvalidAssignmentAccountError,
    InvalidClearanceEntryTypeError,
    CompoundTransactionAssignmentError,
    InsufficientBalanceError,
    OverclearanceError,
    MixedAssignmentError,
)
from .base import Base


class Assignment(IsolatingMixin, Base):
    """Represents an assigment of an assignable to a clearing transaction"""

    # Transaction Types that can be cleared by assignable transactions
    clearables = [
        Transaction.TransactionType[t]
        for t in config.transactions["clearables"]["types"]
    ]

    # Transaction Types that can have clearbale transactions assigned to them
    assignables = [
        Transaction.TransactionType[t]
        for t in config.transactions["assignables"]["types"]
    ]

    assignment_date: Mapped[datetime] = mapped_column()
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transaction.id"), nullable=True
    )
    assigned_id: Mapped[int] = mapped_column()
    assigned_type: Mapped[str] = mapped_column()
    assigned_no: Mapped[str] = mapped_column()
    amount: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4))

    # relationships
    transaction: Mapped["Transaction"] = relationship(foreign_keys=[transaction_id])

    def __repr__(self) -> str:
        return f"Assigning {self.assigned_no} to {self.transaction.transaction_no} on {self.assignment_date} for {self.amount}"

    def assigned(self, session) -> Transaction | Balance:
        """Get the assignable assigned to this assigment's transaction"""
        module = (
            importlib.import_module("python_accounting.models")
            if self.assigned_type in [Transaction.__name__, Balance.__name__]
            else importlib.import_module("python_accounting.transactions")
        )
        return session.get(getattr(module, self.assigned_type), self.assigned_id)

    def validate(self, session) -> None:
        """Validate the assignment properties"""

        if self.amount < 0:
            raise NegativeAmountError(self.__class__.__name__)

        transaction = session.get(Transaction, self.transaction_id)
        if not transaction:
            raise ValueError("The Assignment Transaction was not found")

        if transaction.transaction_type not in Assignment.assignables:
            raise UnassignableTransactionError(
                transaction.__class__.__name__, Assignment.assignables
            )

        if self.assigned_type == Balance.__name__:
            assigned = session.get(Balance, self.assigned_id)
            if not assigned:
                raise ValueError("The Assigned Balance was not found")
        else:
            assigned = session.get(Transaction, self.assigned_id)
            if not assigned:
                raise ValueError("The Assigned Transaction was not found")
            if assigned.transaction_type not in Assignment.clearables:
                raise UnclearableTransactionError(
                    assigned.__class__.__name__, Assignment.clearables
                )
        self.assigned_no = assigned.transaction_no
        if not transaction.is_posted or not assigned.is_posted:
            raise UnpostedAssignmentError

        if transaction.balance(session) < self.amount:
            raise InsufficientBalanceError(
                transaction.__class__.__name__, self.amount, assigned.__class__.__name__
            )

        if assigned.cleared(session) + self.amount > assigned.amount:
            raise OverclearanceError(assigned.__class__.__name__)

        if transaction.compound or assigned.compound:
            raise CompoundTransactionAssignmentError

        if self.transaction_id == self.assigned_id and isinstance(
            assigned, Transaction
        ):
            raise SelfClearanceError

        if transaction.account_id != assigned.account_id:
            raise InvalidAssignmentAccountError

        if transaction.credited == assigned.credited:
            raise InvalidClearanceEntryTypeError(
                Balance.BalanceType.CREDIT
                if transaction.credited
                else Balance.BalanceType.DEBIT
            )

        query = session.query(func.count(Assignment.id))

        if query.filter(Assignment.assigned_id == self.transaction_id).scalar() > 0:
            raise MixedAssignmentError("Cleared", "Assigned")

        if (
            query.filter(Assignment.transaction_id == self.assigned_id).scalar() > 0
            and assigned.transaction_type in Assignment.assignables
        ):
            raise MixedAssignmentError(
                "Assigned",
                "Cleared",
            )
