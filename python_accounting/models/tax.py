# models/tax.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Tax that is applied to the Line Item of a Transaction.

"""

from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, func
from sqlalchemy.types import DECIMAL
from python_accounting.mixins import IsolatingMixin
from python_accounting.models import Recyclable, Account
from python_accounting.exceptions import (
    NegativeValueError,
    MissingTaxAccountError,
    InvalidTaxAccountError,
    HangingTransactionsError,
)


class Tax(IsolatingMixin, Recyclable):
    """Represents a Tax applied to a Transaction's Line Item."""

    __mapper_args__ = {"polymorphic_identity": "Tax"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    """(int): The primary key of the Tax database record."""
    name: Mapped[str] = mapped_column(String(255))
    """(str): The label of the Tax."""
    code: Mapped[str] = mapped_column(String(5))
    """(str): A shorthand representation of the Tax."""
    rate: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4))
    """(Decimal): The percentage rate of the Tax."""
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=True)
    """(int): The id of the Account model to which Tax amounts are posted."""

    # relationships
    account: Mapped["Account"] = relationship(foreign_keys=[account_id])
    """(Account): The Account model to which Tax amounts are posted."""

    def __repr__(self) -> str:
        return f"{self.name} <{self.code}>: {self.rate}"

    def validate(self, session) -> None:
        # pylint: disable=line-too-long
        """
        Validates the Tax properties.

        Args:
            session (Session): The accounting session to which the Balance belongs.

        Raises:
            NegativeValueError: If the Tax rate is less than 0.
            MissingTaxAccountError: If the Tax rate is greater than 0 and the Tax Account is not set.
            InvalidTaxAccountError: If the Tax Account type is not Control.

        Returns:
            None
        """
        # pylint: enable=line-too-long
        if self.rate == 0:
            self.account_id = None

        if self.rate < 0:
            raise NegativeValueError(self.__class__.__name__, "Rate")

        if self.rate > 0 and self.account_id is None:
            raise MissingTaxAccountError

        if (
            session.get(Account, self.account_id).account_type
            != Account.AccountType.CONTROL
        ):
            raise InvalidTaxAccountError

    def validate_delete(self, session) -> None:
        # pylint: disable=line-too-long
        """
        Validates if the Tax can be deleted.

        Args:
            session (Session): The accounting session to which the Tax belongs.

        Raises:
            HangingTransactionsError: If there exists posted Transactions with Line Items that have this Tax applied to them.

        Returns:
            None
        """
        # pylint: enable=line-too-long
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Ledger,
        )

        if (
            session.query(func.count(Ledger.id))  # pylint: disable=not-callable
            .filter(Ledger.entity_id == self.entity_id)
            .filter(Ledger.tax_id == self.id)
            .scalar()
            > 0
        ):
            raise HangingTransactionsError("Tax")
