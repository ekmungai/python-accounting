from sqlalchemy import select
from sqlalchemy.orm import Mapped
from datetime import datetime

from python_accounting.models import Recycled, Entity
from python_accounting.exceptions import SessionEntityError


class SessionOverridesMixin:
    """This class overrides some of sqlalchemy session's in built methods to
    provide accounting specific behavior. It also provides custom methods
    specific to accounting"""

    def get(self, model, primary_key, **kwargs) -> Mapped["Base"]:
        """Override the get method to use select thereby ensuring global filters are applied"""
        return self.scalar(
            select(model).where(model.id == primary_key).execution_options(**kwargs)
        )

    def delete(self, instance) -> bool:
        """Override the delete method to enable model recycling"""

        if isinstance(instance, Entity) and instance.id == self.entity.id:
            raise SessionEntityError
        instance.deleted_at = instance.updated_at = datetime.now()

        self.add(
            Recycled(
                recycled_id=instance.id,
                entity_id=self.entity.id,
            )
        )
        self.commit()
        return True

    def restore(self, instance) -> bool:
        """Restore a deleted instance"""

        if instance.destroyed_at is not None:
            return False  # destroyed models cannot be restored

        recycled = instance.history[-1]
        instance.deleted_at = None
        instance.updated_at = recycled.restored_at = datetime.now()
        self.commit()
        return True

    def destroy(self, instance) -> bool:
        """Destroy (<kind of> permanently delete) an instance"""

        instance.destroyed_at = instance.updated_at = datetime.now()

        self.commit()
        return True

    def erase(self, instance) -> None:
        """Completely remove an instance from the database. Should never be called in production"""

        self.delete(instance)
