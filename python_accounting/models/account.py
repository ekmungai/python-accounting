from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum, func, inspect, Text, select
from python_accounting.mixins import IsolatingMixin
from python_accounting.config import config
from python_accounting.exceptions import InvalidCategoryAccountTypeError
from strenum import StrEnum
from .recyclable import Recyclable
from .reporting_period import ReportingPeriod


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

    def _get_account_code(self, session) -> int:
        """Get the auto generated account code for the instance"""
        current_count = (
            session.query(Account)
            .filter(Account.account_type == self.account_type)
            .with_entities(func.count())
            .scalar()
        )
        return (
            int(config.accounts["types"][self.account_type.name][1])
            + current_count
            + getattr(self, "session_index", 0)
        )

    def __repr__(self) -> str:
        return f"{self.account_type} {self.name} <{self.account_code}>"

    def _balance_movement(
        self, session, start_date: datetime, end_date: datetime
    ) -> dict:
        """Get the change in the account balance between the given dates"""
        from .balance import Balance
        from .ledger import Ledger

        end_date = datetime.today() if not end_date else end_date
        start_date = ReportingPeriod.get_period(
            session, datetime(end_date.year, session.entity.year_start, 1, 0, 0, 0)
        ).interval()["start"]

        query = (
            session.query(func.sum(Ledger.amount).label("amount"))
            .filter(Ledger.currency_id == self.currency_id)
            .filter(Ledger.transaction_date >= start_date)
            .filter(Ledger.transaction_date <= end_date)
            .filter(Ledger.post_account_id == self.id)
        )
        return (
            query.filter(Ledger.entry_type == Balance.BalanceType.DEBIT).scalar() or 0
        ) - (
            query.filter(Ledger.entry_type == Balance.BalanceType.CREDIT).scalar() or 0
        )

    @staticmethod
    def section_balances(
        session,
        account_types,
        start_date: datetime = None,
        end_date: datetime = None,
        full_balance: bool = True,
    ) -> dict:
        """Get the opening, movement and closing balances of the accounts of the given section (account types), organized by category"""
        balances = dict(opening=0, movement=0, closing=0, categories={})

        end_date = datetime.today() if not end_date else end_date
        period_start = ReportingPeriod.get_period(
            session, datetime(end_date.year, session.entity.year_start, 1, 0, 0, 0)
        ).interval()["start"]
        start_date = period_start if not start_date else start_date

        for account in session.scalars(
            select(Account).filter(Account.account_type.in_(account_types))
        ).all():
            account.opening = account.opening_balance(
                session, end_date.year
            ) + account._balance_movement(session, period_start, start_date)
            movement = account._balance_movement(session, start_date, end_date)
            account.closing = account.opening + movement if full_balance else movement
            account.movement = movement * -1  # cashflow purposes
            if account.closing != 0 or account.movement != 0:
                category_id, category_name = (
                    (0, Account.AccountType[account.account_type.name].value)
                    if account.category is None
                    else (account.category_id, account.category.name)
                )
                if category_name in balances["categories"].keys():
                    balances["categories"][category_name]["total"] += account.closing
                    balances["categories"][category_name]["accounts"].append(account)
                else:
                    balances["categories"].update(
                        {
                            category_name: dict(
                                id=category_id,
                                total=account.closing,
                                accounts=[account],
                            )
                        }
                    )
                balances["opening"] += account.opening
                balances["movement"] += account.movement
                balances["closing"] += account.closing
        return balances

    def opening_balance(self, session, year: int = None) -> dict:
        """Get the opening balance for the account for the given year"""
        from .balance import Balance

        period_id = (
            ReportingPeriod.get_period(
                session, datetime(year, session.entity.year_start, 1, 0, 0, 0)
            ).id
            if year
            else session.entity.reporting_period_id
        )
        query = (
            session.query(func.sum(Balance.amount).label("amount"))
            .filter(Balance.currency_id == self.currency_id)
            .filter(Balance.reporting_period_id == period_id)
            .filter(Balance.account_id == self.id)
        )
        return (
            query.filter(Balance.balance_type == Balance.BalanceType.DEBIT).scalar()
            or 0
        ) - (
            query.filter(Balance.balance_type == Balance.BalanceType.CREDIT).scalar()
            or 0
        )

    def closing_balance(self, session, end_date: datetime = None) -> dict:
        """Get the account balance as at the given date"""

        end_date = datetime.today() if not end_date else end_date
        start_date = ReportingPeriod.get_period(
            session, datetime(end_date.year, session.entity.year_start, 1, 0, 0, 0)
        ).interval()["start"]

        return self.opening_balance(session, end_date.year) + self._balance_movement(
            session, start_date, end_date
        )

    def validate(self, session) -> None:
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
