from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum
from typing import List
from strenum import StrEnum
from python_accounting.mixins import IsolatingMixin
from .recyclable import Recyclable
from .account import Account
from python_accounting.exceptions import InvalidAccountTypeError


class Category(IsolatingMixin, Recyclable):
    """Represents a Category of Accounts"""

    __mapper_args__ = {"polymorphic_identity": "Category"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    category_account_type: Mapped[StrEnum] = mapped_column(Enum(Account.AccountType))

    # relationships
    accounts: Mapped[List["Account"]] = relationship(
        back_populates="category", foreign_keys=[Account.category_id]
    )

    def __repr__(self) -> str:
        return f"{self.name} <{self.category_account_type}>"

    def validate(self, session) -> None:
        """Validate the category properties"""

        if self.category_account_type not in Account.AccountType:
            raise InvalidAccountTypeError(
                f"category_account_type must be one of: {', '.join(list(Account.AccountType))}",
            )
