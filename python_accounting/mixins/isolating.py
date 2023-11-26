from sqlalchemy.orm import Mapped, mapped_column, relationship, declared_attr
from sqlalchemy import ForeignKey


class IsolatingMixin:
    """This class enables isolating by Entity for models"""

    entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"))

    @declared_attr
    def entity(self) -> Mapped["Entity"]:
        """Return the entity of the instance"""
        return relationship("Entity", foreign_keys=[self.entity_id])
