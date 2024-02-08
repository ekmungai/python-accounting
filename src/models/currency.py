# models/currency.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Currency as used in Transactions.

"""

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey
from src.mixins import IsolatingMixin
from src.models import Recyclable


class Currency(IsolatingMixin, Recyclable):
    """
    Represents a Currency in terms of a label and an ISO Currency Code.

    Attributes:
        id (int): The primary key of the Category database record.
        name (str): The label of the Currency.
        code (str): The ISO 4217 currency code symbol.

    """

    __mapper_args__ = {"polymorphic_identity": "Currency"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(3))

    def __repr__(self) -> str:
        return f"{self.name} <{self.code}>"
