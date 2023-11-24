class RecyclingMixin:
    """This class grants recycling capability to the database models"""

    def delete(self):
        """Override the database model delete method to enable recycling"""
        pass

    def restore(self):
        """Override the database model delete method to enable recycling"""
        pass

    def destroy(self):
        """Override the database model delete method to enable recycling"""
        pass
