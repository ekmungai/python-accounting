# mixins/assigning.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Provides functionality to assignable Transactions for clearing clearable Transactions.

"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import func, select


class AssigningMixin:
    """
    This class provides assignable Transactions functionality for
    clearing clearable Transactions.

    """

    def balance(self, session) -> Decimal:
        """
        Gets how much of the Transaction amount is remaining available for assigning
            to clearable Transactions.

        Args:
            session (Session): The accounting session to which the Transaction belongs.

        Returns:
            Decimal: The difference between the Transaction
            amount and the total amount of assignments made to it.
        """

        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Assignment,
        )

        return self.amount - (
            (
                session.query(
                    func.sum(Assignment.amount).label(  # pylint: disable=not-callable
                        "amount"
                    )
                )
                .filter(Assignment.transaction_id == self.id)
                .filter(Assignment.entity_id == self.entity_id)
            ).scalar()
            or 0
        )

    def assignments(self, session) -> list:
        """
        Gets the assignments made on the Transaction.

        Args:
            session (Session): The accounting session to which the Transaction belongs.

        Returns:
            A List of assignments made for the Transaction.
        """
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Assignment,
        )

        return session.scalars(
            select(Assignment).filter(Assignment.transaction_id == self.id)
        ).all()

    def unassign(self, session) -> None:
        """
        Removes all assignments made to this Transaction.

        Args:
            session (Session): The accounting session to which the Transaction belongs.

        Returns:
            None
        """
        _ = [session.delete(a) for a in self.assignments(session)]

    def bulk_assign(self, session) -> None:
        """
        Assigns the Transaction's amount to all outstanding clearable Transactions for the
        main account on a FIFO basis.

        Args:
            session (Session): The accounting session to which the Transaction belongs.

        Returns:
            None
        """

        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Assignment,
        )

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
