from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum, func, inspect, Text
from python_accounting.mixins import IsolatingMixin
from python_accounting.config import config
from python_accounting.exceptions import InvalidCategoryAccountTypeError
from strenum import StrEnum
from .recyclable import Recyclable


class Account(IsolatingMixin, Recyclable):
    """Represents an account which groups related Transactions"""

    # Chart of Accounts types
    AccountType = StrEnum(
        "AccountType", {k: v[0] for k, v in config.accounts["types"].items()}
    )

    # Account Types that can be used in Purchasing Transactions
    purchasables = config.accounts["purchasables"]["types"]

    __mapper_args__ = {"polymorphic_identity": "Account"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text(1000), nullable=True)
    account_code: Mapped[int] = mapped_column()
    account_type: Mapped[StrEnum] = mapped_column(Enum(AccountType))
    currency_id: Mapped[int] = mapped_column(ForeignKey("currency.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"), nullable=True)

    # relationships
    currency: Mapped["Currency"] = relationship(foreign_keys=[currency_id])
    category: Mapped["Category"] = relationship(foreign_keys=[category_id])

    def _get_account_code(self, session):
        """Get the auto generated account code for the instance"""
        current_count = (
            session.query(Account)
            .filter(Account.entity_id == self.entity_id)
            .filter(Account.account_type == self.account_type)
            .with_entities(func.count())
            .execution_options(ignore_isolation=True)
            .scalar()
        )
        return (
            int(config.accounts["types"][self.account_type.name][1]) + current_count + 1
        )

    def __repr__(self) -> str:
        return f"{self.account_type} {self.name} <{self.account_code}>"

    def validate(self, session):
        """Validate the reporting period properties"""
        from .category import Category

        self.name = self.name.title()
        if (
            self.account_code is None
            or len(inspect(self).attrs.account_type.history.deleted) > 0
        ):
            self.account_code = self._get_account_code(session)

        if self.category_id:
            category = session.get(Category, self.category_id)
            if self.account_type != category.category_account_type:
                raise InvalidCategoryAccountTypeError(
                    self.account_type.value, category.category_account_type.value
                )
