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
from sqlalchemy import DateTime
from sqlalchemy.types import DECIMAL
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr
from python_accounting.config import config


def amount_type() -> DECIMAL:
    """
    The column type of amounts and quantities.

    Its precision is `config.database["amount_precision"]` (13 by default, so amounts below one
    billion), with 4 decimal places. It is read when the models are imported, so a different
    precision must be set in config.toml or on the config object before importing them.

    Returns:
        DECIMAL: The column type.
    """
    precision = config.database.get("amount_precision", 13)
    if not isinstance(precision, int) or isinstance(precision, bool) or not 5 <= precision <= 38:
        raise ValueError(
            f"amount_precision must be a whole number between 5 and 38, not {precision!r}."
        )
    return DECIMAL(precision=precision, scale=4)


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
    created_at: Mapped[datetime] = mapped_column(default=datetime.now())
    """
    created_at (datetime): The time the database record was created.
    """
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now())
    """
    updated_at (datetime): The time the database record was last modified.
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:  # pylint: disable=no-self-argument
        return cls.__name__.lower()
