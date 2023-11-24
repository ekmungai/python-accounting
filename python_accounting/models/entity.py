from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey
from .base import Base


class Entity(Base):
    """Represents the IFRS's Reporting Entity"""

    __tablename__ = "entity"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    multi_currency: Mapped[bool] = mapped_column(Boolean, default=False)
    mid_year_balances: Mapped[bool] = mapped_column(Boolean, default=False)
    year_start: Mapped[int] = mapped_column(default=1)
    currency_id: Mapped[int] = mapped_column(ForeignKey("currency.id"))

    currency: Mapped["Currency"] = relationship(back_populates="entity")

    def __repr__(self, type_name: bool = False):
        return f"Entity: {self.name}" if type_name else self.name

    # @property
    # def currency(self):
    #     """Returns the Entity's reporting Currency"""
    #     from .currency import Currency

    #     return Currency.get(id=self.currency_id)
