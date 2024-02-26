# models/user.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents an authenicatable User with access to an Entity.

"""

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from python_accounting.mixins import IsolatingMixin
from .base import Base


class User(IsolatingMixin, Base):
    """Represents an authenticatable User with access to an Entity."""

    name: Mapped[str] = mapped_column(String(255))
    """(str): The name of the User."""
    email: Mapped[str] = mapped_column(String(255))
    """(str): A unique email to identify the User."""

    def __repr__(self) -> str:
        return f"{self.name} <{self.email}>"
