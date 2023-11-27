from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from datetime import datetime
from python_accounting.mixins import IsolatingMixin
from .base import Base


class Recycled(IsolatingMixin, Base):
    """Represents an accounting object that has been recycled"""

    recycled_id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"))
    restored_at: Mapped[datetime] = mapped_column(nullable=True)

    # relationships
    subject: Mapped["Recyclable"] = relationship(
        cascade="all,delete", back_populates="history"
    )

    def __repr__(self) -> str:
        return "<{}> {}{}{}".format(
            self.subject.recycled_type,
            f"Deleted: {self.subject.deleted_at} " if self.subject.deleted_at else "",
            f"Restored: {self.restored_at} " if self.restored_at else "",
            f"Destroyed: {self.subject.destroyed_at}"
            if self.subject.destroyed_at
            else "",
        )
