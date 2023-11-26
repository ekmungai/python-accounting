from sqlalchemy.orm import Mapped
from python_accounting.mixins import IsolatingMixin
from .base import Base


class User(IsolatingMixin, Base):
    """Represents an accounting object that has been user"""

    name: Mapped[str]
    email: Mapped[str]

    def __repr__(self) -> str:
        return f"{self.name} <{self.email}>"
