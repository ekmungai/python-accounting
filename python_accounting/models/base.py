# models/base.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents the Base class for accounting models.

"""
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr


# pylint: disable=too-few-public-methods
class Base(DeclarativeBase):
    """The accounting model base class"""

    id: Mapped[int] = mapped_column(primary_key=True)
    """
    id (int): The primary key of the model database record.
    """
    created_at: Mapped[datetime] = mapped_column(default=datetime.now())
    """
    created_at (datetime): The time the database record was created.
    """
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now())
    """
    update_at (datetime): The time the database record was last modified.
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:  # pylint: disable=no-self-argument
        return cls.__name__.lower()
