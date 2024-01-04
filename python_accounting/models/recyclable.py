from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import List
from sqlalchemy import String
from .base import Base


class Recyclable(Base):
    """Interface for associating recycled objects with its models"""

    deleted_at: Mapped[datetime] = mapped_column(nullable=True)
    destroyed_at: Mapped[datetime] = mapped_column(nullable=True)
    recycled_type: Mapped[str] = mapped_column(String(255))

    # relationships
    history: Mapped[List["Recycled"]] = relationship()

    __mapper_args__ = {"polymorphic_on": recycled_type}
