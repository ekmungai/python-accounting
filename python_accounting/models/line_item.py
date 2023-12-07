from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Text, Boolean
from sqlalchemy.types import DECIMAL
from python_accounting.mixins import IsolatingMixin
from .recyclable import Recyclable


class LineItem(IsolatingMixin, Recyclable):
    """Represents a Line Item representing the other side of the double entry of a Transaction"""

    __mapper_args__ = {"polymorphic_identity": "LineItem"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    narration: Mapped[str] = mapped_column(Text(1000))
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4))
    amount: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4))
    vat_inclusive: Mapped[bool] = mapped_column(Boolean, default=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transaction.id"))
    tax_id: Mapped[int] = mapped_column(ForeignKey("tax.id"))

    # relationships
    account: Mapped["Account"] = relationship(foreign_keys=[account_id])
    transaction: Mapped["Transaction"] = relationship(foreign_keys=[transaction_id])

    def __repr__(self) -> str:
        return f"{self.name} <{self.code}>"
