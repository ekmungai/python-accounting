from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy import ForeignKey, Text, Boolean, func, Text, or_
from sqlalchemy.types import DECIMAL
from typing import List, Any
from python_accounting.mixins import IsolatingMixin
from .recyclable import Recyclable
from python_accounting.exceptions import NegativeAmountError, HangingTransactionsError


class LineItem(IsolatingMixin, Recyclable):
    """Represents a Line Item representing the other side of the double entry of a Transaction"""

    __tablename__ = "line_item"

    __mapper_args__ = {"polymorphic_identity": "LineItem"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    narration: Mapped[str] = mapped_column(Text(1000))
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4), default=1)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4))
    credited: Mapped[bool] = mapped_column(Boolean, default=False)
    tax_inclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transaction.id"), nullable=True
    )
    tax_id: Mapped[int] = mapped_column(ForeignKey("tax.id"), nullable=True)

    # relationships
    account: Mapped["Account"] = relationship(foreign_keys=[account_id])
    tax: Mapped["Tax"] = relationship(foreign_keys=[tax_id])
    transaction: Mapped["Transaction"] = relationship(foreign_keys=[transaction_id])
    ledgers: Mapped[List["Ledger"]] = relationship(
        back_populates="line_item",
        primaryjoin="LineItem.id==Ledger.line_item_id",
    )

    @validates("ledgers", include_removes=True)
    def validate_ledgers(self, key, ledger, is_remove):
        raise ValueError(
            f"Line Item ledgers cannot be {'Removed' if is_remove else 'Added'} manually"
        )

    def __init__(self, **kw: Any) -> None:
        self.quantity = 1
        super().__init__(**kw)

    def __repr__(self) -> str:
        return f"{self.account.name if self.account else ''} <{'Credit' if self.credited else 'Debit'}>: {self.amount * self.quantity}"

    def validate(self, session) -> None:
        """Validate the Line Item properties"""

        if self.amount < 0:
            raise NegativeAmountError(self.__class__.__name__)

        if self.quantity and self.quantity < 0:
            raise NegativeAmountError(self.__class__.__name__, "quantity")

    def validate_delete(self, session) -> None:
        """Validate if the line item can be deleted"""
        from python_accounting.models import Ledger

        if (
            session.query(func.count(Ledger.id))
            .filter(Ledger.entity_id == self.entity_id)
            .filter(Ledger.line_item_id == self.id)
            .scalar()
            > 0
        ):
            raise HangingTransactionsError("LineItem")
