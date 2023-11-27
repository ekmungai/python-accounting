from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey
from .recyclable import Recyclable
from typing import List


class Entity(Recyclable):
    """Represents the Reporting Entity"""

    __mapper_args__ = {"polymorphic_identity": "Entity"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    multi_currency: Mapped[bool] = mapped_column(Boolean, default=False)
    mid_year_balances: Mapped[bool] = mapped_column(Boolean, default=False)
    year_start: Mapped[int] = mapped_column(default=1)
    locale: Mapped[str] = mapped_column(String(5), default="en_GB")
    currency_id: Mapped[int] = mapped_column(ForeignKey("currency.id"), nullable=True)

    # relationships
    currency: Mapped["Currency"] = relationship(
        back_populates="entity", foreign_keys=[currency_id]
    )
    users: Mapped[List["User"]] = relationship(back_populates="entity")

    def __repr__(self) -> str:
        return self.name
