# models/balance.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents the amount outstanding on a Transaction from a previous Reporting Period.

"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum, select
from sqlalchemy.types import DECIMAL
from strenum import StrEnum
from python_accounting.models import (
    Recyclable,
    Account,
    Currency,
    ReportingPeriod,
    Transaction,
)
from python_accounting.exceptions import (
    InvalidBalanceAccountError,
    InvalidBalanceTransactionError,
    NegativeValueError,
    InvalidBalanceDateError,
)
from python_accounting.mixins import IsolatingMixin, ClearingMixin
from python_accounting.reports import IncomeStatement


class Balance(IsolatingMixin, ClearingMixin, Recyclable):
    """Represents a Balance brought down from previous Reporting Periods."""

    BalanceType = StrEnum("BalanceType", {"DEBIT": "Debit", "CREDIT": "Credit"})
    """(StrEnum): The double entry types of Balances."""
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
    """(StrEnum): A list of Transaction Types that can have Balances."""

    __mapper_args__ = {"polymorphic_identity": "Balance"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    """(int): The primary key of the Account database record."""
    transaction_date: Mapped[datetime] = mapped_column()
    """(datetime): The date of the Balance Transaction."""
    reference: Mapped[str] = mapped_column(String(255), nullable=True)
    """(`str`, optional): Identifying information about the Balance Transaction."""
    transaction_no: Mapped[str] = mapped_column(String(255))
    """(str): The Transaction number of the Balance Transaction."""
    transaction_type: Mapped[StrEnum] = mapped_column(Enum(BalanceTransactions))
    """(TransactionType): The Transaction type of the Balance Transaction."""
    amount: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4))
    """(Decimal): The amount outstanding on the Balance Transaction."""
    balance_type: Mapped[StrEnum] = mapped_column(Enum(BalanceType))
    """(BalanceType): The side of the double entry to post the Balance amount."""
    currency_id: Mapped[int] = mapped_column(ForeignKey("currency.id"))
    """(int): The id of the Currency model associated with the Balance."""
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    """(int): The id of the Account model to which the Balance belongs."""
    reporting_period_id: Mapped[int] = mapped_column(ForeignKey("reporting_period.id"))
    """(int): The id of the Reporting Period model to which the Balance belongs."""

    # relationships
    currency: Mapped["Currency"] = relationship(foreign_keys=[currency_id])
    """(Currency): The Currency model associated with the Balance."""
    account: Mapped["Account"] = relationship(foreign_keys=[account_id])
    """(Account): The Account model to which the Balance belongs."""
    reporting_period: Mapped["ReportingPeriod"] = relationship(
        foreign_keys=[reporting_period_id]
    )
    """(ReportingPeriod): The Reporting Period model to which the Balance belongs."""

    def __repr__(self) -> str:
        return f"{self.account} {self.reporting_period}: {self.amount}"

    @property
    def is_posted(self) -> bool:
        """is_posted analog for the assignment model."""
        return True

    @property
    def credited(self) -> bool:
        """credited analog for the assignment model."""
        return self.balance_type == Balance.BalanceType.CREDIT

    @property
    def compound(self) -> bool:
        """compound analog for the assignment model."""
        return False

    @staticmethod
    def opening_trial_balance(session, year: int = None) -> dict:
        """
        Gets the total opening balances for the Entity's accounts for the given year.

        Args:
            session (Session): The accounting session to which the Account belongs.
            year (`int`, optional): The calendar year to retrieve the opening
                trial balance for. Defaults to the Balance's Entity current Reporting
                Period's calendar year.

        Returns:
            dict: With a A summary of the debit and credit balances of the Accounts
            together with a list of the Accounts themselves.
                - debits (Decimal): The total debit balance.
                - credits (Decimal): The total credit balance.
                - accounts (Decimal): Accounts constituting the opening trial balance.

        """
        balances = {"debits": 0, "credits": 0, "accounts": []}
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
        # pylint: disable=line-too-long
        """
        Validates the Balance properties.

        Args:
            session (Session): The accounting session to which the Balance belongs.

        Raises:
            NegativeValueError: If the Balance amount is less than 0.
            InvalidBalanceAccountError: If the Balance main Account is an Income Statement Account.
            InvalidBalanceTransactionError: If the Balance Transaction type is not one of the Balance Transaction types.
            InvalidBalanceDateError: If the Balance Transaction date is within the current reporting period and the Entity does not allow mid year balances.

        Returns:
            None
        """
        # pylint:enable=line-too-long
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
            raise NegativeValueError(self.__class__.__name__)

        if account.account_type in [t.value for t in IncomeStatement.Accounts]:
            raise InvalidBalanceAccountError

        if self.transaction_type not in [t.value for t in Balance.BalanceTransactions]:

            raise InvalidBalanceTransactionError

        if (
            reporting_period.interval()["start"] < self.transaction_date
            and not session.entity.mid_year_balances
        ):
            raise InvalidBalanceDateError
