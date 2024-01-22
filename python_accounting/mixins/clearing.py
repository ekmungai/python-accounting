from decimal import Decimal
from sqlalchemy import func, select


class ClearingMixin:
    """This class provides clerarable transactions the total amount cleared"""

    def cleared(self, session) -> Decimal:
        """Get how much of the transaction amount has been cleared by assignable transactions"""
        from python_accounting.models import Assignment

        return (
            session.query(func.sum(Assignment.amount).label("amount"))
            .filter(Assignment.entity_id == self.entity_id)
            .filter(Assignment.assigned_id == self.id)
            .filter(Assignment.assigned_type == self.__class__.__name__)
        ).scalar() or 0

    def clearances(self, session) -> list:
        """Get the assignments used to clear this transaction"""
        from python_accounting.models import Assignment

        return session.scalars(
            select(Assignment)
            .filter(Assignment.assigned_id == self.id)
            .filter(Assignment.assigned_type == self.__class__.__name__)
        ).all()

    def unclear(self, session) -> None:
        """Remove all clearances made on this transaction"""
        [session.delete(a) for a in self.clearances(session)]
