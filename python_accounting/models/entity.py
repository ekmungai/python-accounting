from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey
from .base import Base
from typing import List


class Entity(Base):
    """Represents the IFRS's Reporting Entity"""

    name: Mapped[str] = mapped_column(String(300))
    multi_currency: Mapped[bool] = mapped_column(Boolean, default=False)
    mid_year_balances: Mapped[bool] = mapped_column(Boolean, default=False)
    year_start: Mapped[int] = mapped_column(default=1)
    currency_id: Mapped[int] = mapped_column(ForeignKey("currency.id"), nullable=True)

    # relationships
    currency: Mapped["Currency"] = relationship(
        back_populates="entity", foreign_keys=[currency_id]
    )
    users: Mapped[List["User"]] = relationship(back_populates="entity")

    def __repr__(self) -> str:
        return self.name
