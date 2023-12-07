from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum, Boolean, Text
from sqlalchemy.types import DECIMAL
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
    transaction_date: Mapped[datetime] = mapped_column()
    transaction_no: Mapped[str] = mapped_column(String(255))
    transaction_type: Mapped[StrEnum] = mapped_column(Enum(TransactionType))
    narration: Mapped[str] = mapped_column(Text(1000))
    reference: Mapped[str] = mapped_column(String(255), nullable=True)
    main_account_amount: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4))
    credited: Mapped[bool] = mapped_column(Boolean, default=True)
    compound: Mapped[bool] = mapped_column(Boolean, default=False)
    currency_id: Mapped[int] = mapped_column(ForeignKey("currency.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))

    # relationships
    currency: Mapped["Currency"] = relationship(foreign_keys=[currency_id])
    account: Mapped["Account"] = relationship(foreign_keys=[account_id])

    def __repr__(self) -> str:
        return f"{self.account} <{self.transaction_no}>: {self.amount}"
