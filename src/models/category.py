# models/category.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents the Base class for accounting models.

"""

from typing import List
from datetime import datetime
from strenum import StrEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum
from src.mixins import IsolatingMixin
from src.models import Recyclable, Account
from src.exceptions import InvalidAccountTypeError
from src.utils.dates import get_dates


class Category(IsolatingMixin, Recyclable):
    """
    Represents a grouping of Accounts of the same type.

    Attributes:
        id (int): The primary key of the Category database record.
        category_account_type (:obj:`list` of :obj:`Account.AccountType`): The Account
            type of the members of the Category.
        name (str): The label of the Category.

    """

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

    def validate(self, _) -> None:
        """
        Validates the Category properties.

        Args:
            session (Session): The accounting session to which the Category belongs.

        Raises:
            InvalidAccountTypeError: If the category account type is not one of
            Account.AccountType.

        Returns:
            None
        """

        if self.category_account_type not in Account.AccountType:
            raise InvalidAccountTypeError(
                f"category_account_type must be one of: {', '.join(list(Account.AccountType))}.",
            )

    def account_balances(self, session, end_date: datetime = None) -> dict:
        """
        Returns the Accounts belonging to the Category and their balances.

        Args:
            session (Session): The accounting session to which the Account belongs.
            end_date (datetime): The latest transaction date for Transaction amounts to be included
                in the Account balances.

        Returns:
            dict: With a A summary of the total of the Account balances of the together with a list
            of the Accounts themselves.
        """

        _, end_date, _, _ = get_dates(session, None, end_date)

        balances = dict(total=0, accounts=[])

        for account in self.accounts:
            account.balance = account.closing_balance(session, end_date)

            if account.balance != 0:
                balances["total"] += account.balance
                balances["accounts"].append(account)

        return balances
