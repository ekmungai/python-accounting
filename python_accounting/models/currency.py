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
from python_accounting.mixins import IsolatingMixin
from python_accounting.models import Recyclable


class Currency(IsolatingMixin, Recyclable):
    """Represents a Currency in terms of a label and an ISO Currency Code."""

    __mapper_args__ = {"polymorphic_identity": "Currency"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    """(int): The primary key of the Category database record."""
    name: Mapped[str] = mapped_column(String(255))
    """(str): The label of the Currency."""
    code: Mapped[str] = mapped_column(String(3))
    """(str): The ISO 4217 currency code symbol."""

    def __repr__(self) -> str:
        return f"{self.name} <{self.code}>"
