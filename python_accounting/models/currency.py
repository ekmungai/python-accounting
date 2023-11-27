from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey
from python_accounting.mixins import IsolatingMixin
from .recyclable import Recyclable

# from .entity import Entity


class Currency(IsolatingMixin, Recyclable):
    """Represents a currency defined by a name/label and an ISO currency code"""

    __mapper_args__ = {"polymorphic_identity": "Currency"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    code: Mapped[str] = mapped_column(String(3))

    def __repr__(self) -> str:
        return f"{self.name} <{self.code}>  <{self.id}>"
