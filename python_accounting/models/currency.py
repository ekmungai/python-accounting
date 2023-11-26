from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from python_accounting.mixins import IsolatingMixin
from .base import Base

# from .entity import Entity


class Currency(IsolatingMixin, Base):
    """Represents a currency defined by a name/label and an ISO currency code"""

    name: Mapped[str] = mapped_column(String(300))
    code: Mapped[str] = mapped_column(String(3))

    def __repr__(self) -> str:
        return f"{self.name} <{self.code}>"
