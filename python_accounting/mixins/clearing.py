# mixins/clearing.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Provides functionality to clearable Transactions for assignment to assignable Transactions.

"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import func, select


class ClearingMixin:
    """
    This class provides clearable Transactions functionality for assigning them to
    assignable Transactions.
    """

    def cleared(self, session, end_date: datetime = None) -> Decimal:
        """
        Gets how much of the Transaction amount has been cleared by assignable Transactions.

        Args:
            session (Session): The accounting session to which the Transaction belongs.
            end_date (datetime, optional): Include assignments at or before this timestamp.
                Defaults to all assignments.

        Returns:
            Decimal: The total amount of assignments made against Transaction.
        """
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Assignment,
        )

        query = (
            session.query(
                func.sum(Assignment.amount).label(  # pylint: disable=not-callable
                    "amount"
                )
            )
            .filter(Assignment.entity_id == self.entity_id)
            .filter(Assignment.assigned_id == self.id)
            .filter(Assignment.assigned_type == self.__class__.__name__)
        )
        if end_date is not None:
            query = query.filter(Assignment.assignment_date <= end_date)

        return query.scalar() or 0

    def clearances(self, session) -> list:
        """
        Gets the assignments made to clear the Transaction.

        Args:
            session (Session): The accounting session to which the Transaction belongs.

        Returns:
            A List of assignments made to clear the Transaction.
        """
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Assignment,
        )

        return session.scalars(
            select(Assignment)
            .filter(Assignment.assigned_id == self.id)
            .filter(Assignment.assigned_type == self.__class__.__name__)
        ).all()

    def unclear(self, session) -> None:
        """
        Removes all assignments made to clear this Transaction.

        Args:
            session (Session): The accounting session to which the Transaction belongs.

        Returns:
            None
        """
        _ = [session.delete(a) for a in self.clearances(session)]
