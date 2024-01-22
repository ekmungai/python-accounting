from datetime import datetime
from decimal import Decimal
from sqlalchemy import func, select


class AssigningMixin:
    """This class provides assignable transactions the remaining balance available for clearing"""

    def balance(self, session) -> Decimal:
        """Get how much of the transaction amount has been assigned to clearable transactions"""
        from python_accounting.models import Assignment

        return self.amount - (
            (
                session.query(func.sum(Assignment.amount).label("amount")).filter(
                    Assignment.transaction_id == self.id
                )
            ).scalar()
            or 0
        )

    def assignments(self, session) -> list:
        """Get the assignments used to assign this transaction"""
        from python_accounting.models import Assignment

        return session.scalars(
            select(Assignment).filter(Assignment.transaction_id == self.id)
        ).all()

    def unassign(self, session) -> None:
        """Remove all assignments made to this transaction"""
        [session.delete(a) for a in self.assignments(session)]

    def bulk_assign(self, session) -> None:
        """Assign this transanction to all outstanding transactions for the main account on a FIFO basis"""
        from python_accounting.models import Assignment

        balance = self.balance(session)

        for clearable in self.account.statement(session, None, None, True)[
            "transactions"
        ]:
            assignment = Assignment(
                assignment_date=datetime.now(),
                transaction_id=self.id,
                assigned_id=clearable.id,
                assigned_type=clearable.__class__.__name__,
                entity_id=self.entity_id,
            )

            assignment.amount = (
                balance
                if clearable.uncleared_amount > balance
                else clearable.uncleared_amount
            )
            balance -= clearable.uncleared_amount
            session.add(assignment)
            session.flush()
