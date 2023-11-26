class RecyclingMixin:
    """This class enables recycling for models"""

    @property
    def is_deleted(self):
        """Check if the model has been deleted"""
        return self.deleted_at or self.destroyed_at
