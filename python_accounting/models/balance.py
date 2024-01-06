from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum, select
from sqlalchemy.types import DECIMAL
from strenum import StrEnum
from .recyclable import Recyclable
from .account import Account
from .currency import Currency
from .reporting_period import ReportingPeriod
from .transaction import Transaction
from python_accounting.exceptions import (
    InvalidBalanceAccountError,
    InvalidBalanceTransactionError,
    NegativeAmountError,
    InvalidBalanceDateError,
)
from python_accounting.mixins import IsolatingMixin, ClearingMixin
from python_accounting.reports import IncomeStatement


class Balance(IsolatingMixin, ClearingMixin, Recyclable):
    """Represents a Balance brought down from previous reporting periods"""

    BalanceType = StrEnum("BalanceType", {"DEBIT": "Debit", "CREDIT": "Credit"})
    BalanceTransactions = StrEnum(
        "BalanceTransactions",
        {
            t.name: t.value
            for t in [
                Transaction.TransactionType.CLIENT_INVOICE,
                Transaction.TransactionType.SUPPLIER_BILL,
                Transaction.TransactionType.JOURNAL_ENTRY,
            ]
        },
    )

    __mapper_args__ = {"polymorphic_identity": "Balance"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    transaction_date: Mapped[datetime] = mapped_column()
    reference: Mapped[str] = mapped_column(String(255), nullable=True)
    transaction_no: Mapped[str] = mapped_column(String(255))
    transaction_type: Mapped[StrEnum] = mapped_column(Enum(BalanceTransactions))
    amount: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4))
    balance_type: Mapped[StrEnum] = mapped_column(Enum(BalanceType))
    currency_id: Mapped[int] = mapped_column(ForeignKey("currency.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    reporting_period_id: Mapped[int] = mapped_column(ForeignKey("reporting_period.id"))

    # relationships
    currency: Mapped["Currency"] = relationship(foreign_keys=[currency_id])
    account: Mapped["Account"] = relationship(foreign_keys=[account_id])
    reporting_period: Mapped["ReportingPeriod"] = relationship(
        foreign_keys=[reporting_period_id]
    )

    def __repr__(self) -> str:
        return f"{self.account} {self.reporting_period}: {self.amount}"

    @property
    def is_posted(self) -> bool:
        """is_posted analog for the assignment model"""
        return True

    @property
    def credited(self) -> bool:
        """credited analog for the assignment model"""
        return self.balance_type == Balance.BalanceType.CREDIT

    @property
    def compound(self) -> bool:
        """compound analog for the assignment model"""
        return False

    @staticmethod
    def opening_trial_balance(session, year: int = None) -> dict:
        """Get the total opening balances for the entity's accounts for the given year"""
        balances = dict(debits=0, credits=0, accounts=[])
        year = session.entity.reporting_period.calendar_year if not year else year

        for account in session.scalars(select(Account)).all():
            balance = account.opening_balance(session, year)
            if balance != 0:
                balances["accounts"].append(account)
                if balance > 0:
                    balances["debits"] += balance
                else:
                    balances["credits"] += balance
        return balances

    def validate(self, session) -> None:
        """Validate the Balance properties"""

        reporting_period = session.entity.reporting_period
        account = session.get(Account, self.account_id)
        self.currency_id = account.currency_id
        self.reporting_period_id = reporting_period.id

        if not self.transaction_no:
            currency = session.get(Currency, self.currency_id)
            self.transaction_no = (
                f"{self.account_id}{currency.code}{reporting_period.calendar_year}"
            )

        if self.amount < 0:
            raise NegativeAmountError(self.__class__.__name__)

        if account.account_type in IncomeStatement.Accounts:
            raise InvalidBalanceAccountError

        if self.transaction_type not in Balance.BalanceTransactions:
            raise InvalidBalanceTransactionError

        if (
            reporting_period.interval()["start"] < self.transaction_date
            and not session.entity.mid_year_balances
        ):
            raise InvalidBalanceDateError
