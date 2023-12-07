from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Enum
from python_accounting.mixins import IsolatingMixin
from python_accounting.config import config
from strenum import StrEnum
from .recyclable import Recyclable


class Transaction(IsolatingMixin, Recyclable):
    """Represents a Transaction in the sense of an original source document"""

    # Transaction types
    TransactionType = StrEnum(
        "TransactionType", {k: v for k, v in config.transactions["types"].items()}
    )

    __mapper_args__ = {"polymorphic_identity": "Transaction"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    transaction_type: Mapped[StrEnum] = mapped_column(Enum(TransactionType))

    def __repr__(self) -> str:
        return f"{self.name} <{self.code}>"
