from sqlalchemy import select, and_
from sqlalchemy.orm import Mapped
from datetime import datetime

from python_accounting.models import Recycled, Recyclable
from python_accounting.exceptions import SessionEntityError


class SessionOverridesMixin:
    """This class overrides some of sqlalchemy's in built methods to
    provide accounting specific behavior. It also provides custom methods
    specific to accounting"""

    def get(self, model, primary_key, **kwargs) -> Mapped["Base"]:
        """Override the get method to use select thereby ensuring global filters are applied"""
        return self.scalar(
            select(model).where(model.id == primary_key).execution_options(**kwargs)
        )

    def delete(self, instance) -> bool:
        """Override the delete method to enable model recycling"""

        if instance.id == self.entity.id:
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

    def destroy(self, instance) -> bool:
        """Destroy (permanently delete) an instance"""

        if instance.destroyed_at is not None:
            return False  # destroyed models cannot be restored

        instance.destroyed_at = instance.updated_at = datetime.now()

        self.commit()
