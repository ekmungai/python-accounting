from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey
from .base import Base

# from .entity import Entity


class Currency(Base):
    """Represents a currency defined by a name/label and an ISO currency code"""

    __tablename__ = "currency"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    code: Mapped[str] = mapped_column(String(3))
    # entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"))

    entity: Mapped["Entity"] = relationship(back_populates="currency")
