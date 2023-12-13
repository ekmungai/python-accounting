from decimal import Decimal
from typing import Any
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Text, Boolean
from sqlalchemy.types import DECIMAL
from python_accounting.mixins import IsolatingMixin
from .recyclable import Recyclable
from python_accounting.exceptions import (
    NegativeAmountError,
)


class LineItem(IsolatingMixin, Recyclable):
    """Represents a Line Item representing the other side of the double entry of a Transaction"""

    __tablename__ = "line_item"

    __mapper_args__ = {"polymorphic_identity": "LineItem"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    narration: Mapped[str] = mapped_column(Text(1000))
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4), default=1)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4))
    credited: Mapped[bool] = mapped_column(Boolean, default=False)
    vat_inclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transaction.id"), nullable=True
    )
    tax_id: Mapped[int] = mapped_column(ForeignKey("tax.id"), nullable=True)

    # relationships
    account: Mapped["Account"] = relationship(foreign_keys=[account_id])
    tax: Mapped["Tax"] = relationship(foreign_keys=[tax_id])
    transaction: Mapped["Transaction"] = relationship(foreign_keys=[transaction_id])

    def __init__(self, **kw: Any):
        self.quantity = 1
        super().__init__(**kw)

    def __repr__(self) -> str:
        return f"{self.account.name if self.account else ''} <{'Credit' if self.credited else 'Debit'}>: {self.amount * self.quantity}"

    def validate(self, session):
        """Validate the Line Item properties"""

        if self.amount < 0:
            raise NegativeAmountError(self.__class__.__name__)

        if self.quantity and self.quantity < 0:
            raise NegativeAmountError(self.__class__.__name__, "quantity")
