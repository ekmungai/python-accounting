from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    ForeignKey,
    Enum,
    Boolean,
    Text,
    func,
    UniqueConstraint,
    inspect,
    CheckConstraint,
)
from sqlalchemy.types import DECIMAL
from python_accounting.mixins import IsolatingMixin
from python_accounting.config import config
from python_accounting.exceptions import (
    InvalidTransactionDateError,
    ClosedReportingPeriodError,
    AdjustingReportingPeriodError,
    RedundantTransactionError,
)
from strenum import StrEnum
from typing import List, Set
from .recyclable import Recyclable
from .account import Account
from .reporting_period import ReportingPeriod
from .line_item import LineItem


class Transaction(IsolatingMixin, Recyclable):
    """Represents a Transaction in the sense of an original source document"""

    __table_args__ = (UniqueConstraint("transaction_no", "entity_id"),)

    # Transaction types
    TransactionType = StrEnum(
        "TransactionType", {k: v[0] for k, v in config.transactions["types"].items()}
    )

    __mapper_args__ = {"polymorphic_identity": "Transaction"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    transaction_date: Mapped[datetime] = mapped_column()
    transaction_no: Mapped[str] = mapped_column(String(255), nullable=True)
    transaction_type: Mapped[StrEnum] = mapped_column(Enum(TransactionType))
    narration: Mapped[str] = mapped_column(Text(1000))
    reference: Mapped[str] = mapped_column(String(255), nullable=True)
    main_account_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=13, scale=4), default=0
    )
    credited: Mapped[bool] = mapped_column(Boolean, default=True)
    compound: Mapped[bool] = mapped_column(Boolean, default=False)
    currency_id: Mapped[int] = mapped_column(ForeignKey("currency.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))

    # relationships
    currency: Mapped["Currency"] = relationship(foreign_keys=[currency_id])
    account: Mapped["Account"] = relationship(foreign_keys=[account_id])
    line_items: Mapped[Set["LineItem"]] = relationship(
        back_populates="transaction",
        primaryjoin="Transaction.id==LineItem.transaction_id",
    )

    @property
    def tax(self):
        """The taxes that have been applied to the transaction"""
        taxes = dict()
        total = 0
        for line_item in iter(self.line_items):
            if line_item.tax_id:
                amount = (
                    line_item.tax.rate * line_item.amount * line_item.quantity / 100
                )
                total += amount
                if line_item.tax.code in taxes.keys():
                    taxes[line_item.tax.code]["amount"] += amount
                else:
                    taxes.update(
                        {
                            line_item.tax.code: dict(
                                name=line_item.tax.name,
                                rate=f"{round(line_item.tax.rate, 2)}%",
                                amount=amount,
                            )
                        }
                    )
        return dict(total=total, taxes=taxes)

    @property
    def amount(self):
        """The amount of the transaction"""
        return 0

    def __repr__(self) -> str:
        return f"{self.account} <{self.transaction_no}>: {self.amount}"

    def _transaction_no(self, transaction_type, session, reporting_period):
        """Get the next auto-generated transaction number"""
        next_id = (
            session.query(Transaction)
            .filter(Transaction.transaction_type == transaction_type)
            .filter(Transaction.transaction_date > reporting_period.interval()["start"])
            .with_entities(func.count())
            .execution_options(include_deleted=True)
            .scalar()
        ) + self.prefix_index

        prefix = config.transactions["types"][transaction_type.name][1]
        return f"{prefix}{reporting_period.period_count:02}/{next_id:04}"

    def validate(self, session):
        """Validate the Transaction properties"""

        account = session.get(Account, self.account_id)
        reporting_period = ReportingPeriod.get_period(self.transaction_date, session)
        self.currency_id = account.currency_id

        if reporting_period.status == ReportingPeriod.Status.CLOSED:
            raise ClosedReportingPeriodError(reporting_period)

        if (
            reporting_period.status == ReportingPeriod.Status.ADJUSTING
            and self.transaction_type != Transaction.TransactionType.JOURNAL_ENTRY
        ):
            raise AdjustingReportingPeriodError(reporting_period)

        if (
            self.transaction_date
            and self.transaction_date == reporting_period.interval()["start"]
        ):
            raise InvalidTransactionDateError

        # if self.id and len(inspect(self).attrs.transaction_type.history.deleted) > 0:
        #     raise InvalidTransactionTypeError
        # TODO

        if not self.transaction_no:
            self.transaction_no = self._transaction_no(
                self.transaction_type, session, reporting_period
            )

        for line_item in self.line_items:
            if line_item.account_id == self.account_id:
                raise RedundantTransactionError(line_item)
