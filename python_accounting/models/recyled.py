from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from python_accounting.mixins import IsolatingMixin
from .base import Base


class Recycled(IsolatingMixin, Base):
    """Represents an accounting object that has been recycled"""

    recycled_type: Mapped[str] = mapped_column(String(300))
    recycled_id: Mapped[int] = mapped_column()

    def __repr__(self) -> str:
        return f"{self.name} <{self.email}>"
