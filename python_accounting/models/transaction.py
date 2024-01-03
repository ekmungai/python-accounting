from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
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
    MissingLineItemError,
    PostedTransactionError,
)
from strenum import StrEnum
from typing import List, Set
from .recyclable import Recyclable
from .account import Account
from .reporting_period import ReportingPeriod
from .line_item import LineItem


class Transaction(IsolatingMixin, Recyclable):
    """Represents a Transaction in the sense of an original source document"""

    # Transaction types
    TransactionType = StrEnum(
        "TransactionType", {k: v[0] for k, v in config.transactions["types"].items()}
    )

    __table_args__ = (UniqueConstraint("transaction_no", "entity_id"),)
    __tablename__ = "transaction"
    __mapper_args__ = {
        "polymorphic_identity": "Transaction",
    }

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
    ledgers: Mapped[List["Ledger"]] = relationship(
        back_populates="transaction",
        primaryjoin="Transaction.id==Ledger.transaction_id",
    )

    @validates("line_items", include_removes=True)
    def validate_line_items(self, key, line_item, is_remove):
        if hasattr(self, "_validate_subclass_line_items"):
            self._validate_subclass_line_items(line_item)

        if self.is_posted:
            raise PostedTransactionError(
                f"Cannot {'Remove' if is_remove else 'Add'} Line Items from a Posted Transaction"
            )

        if line_item.id is None:
            raise ValueError(
                "Line Item must be persisted to be added to the Transaction"
            )

        if not self.compound and line_item.credited == self.credited:
            line_item.credited = not self.credited
        return line_item

    @validates("ledgers", include_removes=True)
    def validate_ledgers(self, key, ledger, is_remove):
        raise ValueError(
            f"Transaction ledgers cannot be {'Removed' if is_remove else 'Added'} manually"
        )

    @property
    def tax(self) -> dict:
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
    def is_posted(self) -> Decimal:
        """Check if the Transaction has been posted to the ledger"""
        return len(self.ledgers) > 0

    @property
    def amount(self) -> Decimal:
        """The amount of the transaction"""

        return sum(
            [
                l.amount * l.quantity
                + (
                    (l.amount * l.quantity * l.tax.rate / 100)
                    if l.tax_id and not l.tax_inclusive
                    else 0
                )
                for l in iter(self.line_items)
                if l.credited != self.credited
            ]
        )

    def __repr__(self) -> str:
        return f"{self.account} <{self.transaction_no}>: {self.amount}"

    def _get_main_account(self, session, account_id: int) -> Account:
        """Retrieve the main account of the tranaction from the database"""
        account = session.get(Account, self.account_id)
        if not account:
            raise ValueError("The main Account is required")
        return account

    def _transaction_no(self, session, transaction_type, reporting_period) -> str:
        """Get the next auto-generated transaction number"""
        next_id = (
            session.query(Transaction)
            .filter(Transaction.transaction_type == transaction_type)
            .filter(Transaction.transaction_date > reporting_period.interval()["start"])
            .with_entities(func.count())
            .execution_options(include_deleted=True)
            .scalar()
        ) + getattr(self, "session_index", 1)

        prefix = config.transactions["types"][transaction_type.name][1]
        return f"{prefix}{reporting_period.period_count:02}/{next_id:04}"

    def post(self, session) -> None:
        """Post the Transaction to the Ledger"""
        from .ledger import Ledger

        if not self.line_items:
            raise MissingLineItemError

        session.flush()
        Ledger.post(session, self)

    def contribution(self, session, account: Account) -> Decimal:
        """Get the amount contributed by the account to the transaction total"""
        from .balance import Balance
        from .ledger import Ledger

        query = (
            session.query(func.sum(Ledger.amount).label("amount"))
            .filter(Ledger.entity_id == self.entity_id)
            .filter(Ledger.transaction_id == self.id)
            .filter(Ledger.currency_id == self.currency_id)
            .filter(Ledger.post_account_id == account.id)
        )
        return (
            query.filter(Ledger.entry_type == Balance.BalanceType.DEBIT).scalar()
            or 0
            - query.filter(Ledger.entry_type == Balance.BalanceType.CREDIT).scalar()
            or 0
        )

    def validate(self, session) -> None:
        """Validate the Transaction properties"""

        if self.is_posted:
            raise PostedTransactionError(f"A Posted Transaction cannot be modified")

        account = self._get_main_account(session, self.account_id)

        reporting_period = ReportingPeriod.get_period(
            session,
            self.transaction_date,
        )
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
                session, self.transaction_type, reporting_period
            )

        for line_item in self.line_items:
            if line_item.account_id == self.account_id:
                raise RedundantTransactionError(line_item)
