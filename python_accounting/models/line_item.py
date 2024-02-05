# models/line_item.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents the individual entries in a Transaction that will eventually be posted to the Ledger.

"""

from decimal import Decimal
from typing import List, Any
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy import ForeignKey, Text, Boolean, func, Text
from sqlalchemy.types import DECIMAL
from python_accounting.mixins import IsolatingMixin
from python_accounting.models import Recyclable
from python_accounting.exceptions import NegativeAmountError, HangingTransactionsError


class LineItem(IsolatingMixin, Recyclable):
    """
    Represents a Line Item which the other side of the double entry from the main account
    of a Transaction.

    Attributes:
        id (int): The primary key of the Line Item database record.
        narration (str): A short description of the Line Item's contribution to the
            Transaction.
        quantity (Decimal): The multiple of the Line Item amount to be posted to the
            Ledger.
        amount (Decimal): The amount to be posted to the Line Item Account.
        credited (:obj:`bool`, optional): Determines whether the Line Item amount will
            be posted to the credit side of the Line Item Account. Defaults to False.
        tax_inclusive (:obj:`bool`, optional): Determines whether the Tax amount of the
            Line Item is included in the Line Item amount. Defaults to False.
        account_id (int): The id of the Account model associated with the Line Item.
        transaction_id (:obj:`int`, optional): The id of the Transaction model associated
            with the Line Item.
        tax_id (:obj:`int`, optional): The id of the Tax model associated with the Line Item.

    """

    __tablename__ = "line_item"

    __mapper_args__ = {"polymorphic_identity": "LineItem"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    narration: Mapped[str] = mapped_column(Text(1000))
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4), default=1)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4))
    credited: Mapped[bool] = mapped_column(Boolean, default=False)
    tax_inclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"))
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transaction.id"), nullable=True
    )
    tax_id: Mapped[int] = mapped_column(ForeignKey("tax.id"), nullable=True)

    # relationships
    account: Mapped["Account"] = relationship(foreign_keys=[account_id])
    tax: Mapped["Tax"] = relationship(foreign_keys=[tax_id])
    transaction: Mapped["Transaction"] = relationship(foreign_keys=[transaction_id])
    ledgers: Mapped[List["Ledger"]] = relationship(
        back_populates="line_item",
        primaryjoin="LineItem.id==Ledger.line_item_id",
    )

    @validates("ledgers", include_removes=True)
    def validate_ledgers(self, key, ledger, is_remove):
        """validates adding or removing of Line Item Ledgers."""
        raise ValueError(
            f"Line Item ledgers cannot be {'Removed' if is_remove else 'Added'} manually."
        )

    def __init__(self, **kw: Any) -> None:
        self.quantity = 1
        super().__init__(**kw)

    def __repr__(self) -> str:
        return f"""{self.account.name if self.account else ''}
         <{'Credit' if self.credited else 'Debit'}>: {self.amount * self.quantity}"""

    def validate(self, _) -> None:
        """
        Validates the Line Item properties.

        Args:
            session (Session): The accounting session to which the Line Item belongs.

        Raises:
            NegativeAmountError: If the Line Item amount or quantity is less than 0.

        Returns:
            None

        """

        if self.amount < 0:
            raise NegativeAmountError(self.__class__.__name__)

        if self.quantity and self.quantity < 0:
            raise NegativeAmountError(self.__class__.__name__, "quantity")

    def validate_delete(self, session) -> None:
        """
        Validates if the line item can be deleted.

        """
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Ledger,
        )

        if (
            session.query(func.count(Ledger.id))  # pylint: disable=not-callable
            .filter(Ledger.entity_id == self.entity_id)
            .filter(Ledger.line_item_id == self.id)
            .scalar()
            > 0
        ):
            raise HangingTransactionsError("LineItem")
