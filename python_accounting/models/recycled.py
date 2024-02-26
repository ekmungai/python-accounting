# models/recycled.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents an account model that has been recycled.

"""

from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from python_accounting.mixins import IsolatingMixin
from .base import Base


class Recycled(IsolatingMixin, Base):
    """Represents an accounting model that has been recycled."""

    recycled_id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"))
    """(int): The id of the model that has been recycled."""
    restored_at: Mapped[datetime] = mapped_column(nullable=True)
    """(`datetime`, optional): The time the model was restored."""

    # relationships
    subject: Mapped["Recyclable"] = relationship(
        cascade="all,delete", back_populates="history"
    )
    """(Recyclable): The model that was recycled/restored."""

    def __repr__(self) -> str:
        return "<{}> {}{}{}".format(  # pylint: disable=consider-using-f-string
            self.subject.recycled_type,
            f"Deleted: {self.subject.deleted_at} " if self.subject.deleted_at else "",
            f"Restored: {self.restored_at} " if self.restored_at else "",
            (
                f"Destroyed: {self.subject.destroyed_at}"
                if self.subject.destroyed_at
                else ""
            ),
        )
