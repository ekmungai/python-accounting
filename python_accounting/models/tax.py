from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum
from sqlalchemy.types import DECIMAL
from python_accounting.mixins import IsolatingMixin
from .recyclable import Recyclable
from .account import Account
from python_accounting.exceptions import (
    NegativeAmountError,
    MissingTaxAccountError,
    InvalidTaxAccountError,
)


class Tax(IsolatingMixin, Recyclable):
    """Represents a Tax applied to a Transaction's line item"""

    __mapper_args__ = {"polymorphic_identity": "Tax"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(5))
    rate: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4))
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=True)

    # relationships
    account: Mapped["Account"] = relationship(foreign_keys=[account_id])

    def __repr__(self) -> str:
        return f"{self.name} <{self.code}>: {self.rate}"

    def validate(self, session):
        """Validate the Tax properties"""

        if self.rate == 0:
            self.account_id = None

        if self.rate < 0:
            raise NegativeAmountError(self.__class__.__name__, "Rate")

        if self.rate > 0 and self.account_id is None:
            raise MissingTaxAccountError

        if (
            session.get(Account, self.account_id).account_type
            != Account.AccountType.CONTROL
        ):
            raise InvalidTaxAccountError
