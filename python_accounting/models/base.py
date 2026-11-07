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
from sqlalchemy import DateTime, event
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr


# pylint: disable=too-few-public-methods
class Base(DeclarativeBase):
    """The accounting model base class"""

    # MySQL rounds DATETIME to the second by default, which changes the dates that
    # Ledger hashes are verified against.
    type_annotation_map = {
        datetime: DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql", "mariadb")
    }

    id: Mapped[int] = mapped_column(primary_key=True)
    """
    id (int): The primary key of the model database record.
    """
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    """
    created_at (datetime): The time the database record was created.
    """
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now)
    """
    updated_at (datetime): The time the database record was last modified.
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:  # pylint: disable=no-self-argument
        return cls.__name__.lower()


@event.listens_for(Base, "before_update", propagate=True)
def _set_updated_at(mapper, connection, target) -> None:  # pylint: disable=unused-argument
    """
    Records the modification time of an updated model.

    A column `onupdate` is not enough: for models that inherit from Recyclable, `updated_at` is on
    the recyclable table, which is not updated when only the model's own columns change.
    """
    target.updated_at = datetime.now()
