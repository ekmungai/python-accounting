# models/reporting_period.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a financial cycle of an Entity.

"""
from enum import Enum
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, UniqueConstraint, func, select
from python_accounting.mixins import IsolatingMixin
from python_accounting.exceptions import (
    DuplicateReportingPeriodError,
    MissingReportingPeriodError,
    MultipleOpenPeriodsError,
)
from python_accounting.models import Recyclable


class ReportingPeriod(IsolatingMixin, Recyclable):
    """Represents a financial cycle for the Reporting Entity."""

    __tablename__ = "reporting_period"
    __table_args__ = (
        UniqueConstraint("calendar_year", "entity_id"),
        UniqueConstraint("period_count", "entity_id"),
    )

    class Status(Enum):
        """Represents a Reporting Period's status."""

        OPEN = 0
        """The period is current and Transactions may be posted to it."""
        ADJUSTING = 1
        """
        The period is past and only Journal Entry Transactions may be posted to
        it (E.g Audit Adjustments).
        """
        CLOSED = 2
        """The period is past and no more Transactions may be posted to it."""

    __mapper_args__ = {"polymorphic_identity": "ReportingPeriod"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    """(int): The primary key of the Reporting Period database record."""
    calendar_year: Mapped[int] = mapped_column()
    """(int): The calendar year associated with the ReportingPeriod."""
    period_count: Mapped[int] = mapped_column()
    """(int): The number of periods since the system has been in use by the Entity."""
    status: Mapped[Status] = mapped_column(default=Status.OPEN)
    """(ReportingPeriod.Status): The status of the Reporting Period."""

    def __repr__(self) -> str:
        return f"{self.calendar_year} <Period {self.period_count}>"

    @staticmethod
    def date_year(date: datetime = None, entity=None) -> int:
        """
        Returns the calendar year for the given date.

        Args:
            date (`datetime`, optional): The date whose calendar year is
                to be found. Defaults to the current date.
            entity (`int`, optional): The Entity for whom the calendar year
                is to be found. If absent, defaults to the calendar year.

        Returns:
            int: The calendar year.
        """

        today = datetime.today()
        if not entity:
            return today.year

        month, year = (date.month, date.year) if date else (today.month, today.year)
        return year if month >= entity.year_start else year - 1

    @staticmethod
    def get_period(session, date: datetime) -> "ReportingPeriod":
        """
        Returns the reporting period for the given date.

        Args:
            session (Session): The accounting session to which the Reporting Period
                 belongs.
            date (datetime): The date whose Reporting Period is to be found.

        Raises:
            MissingReportingPeriodError: If there no Reporting Period exists for the
                given date.

        Returns:
            ReportingPeriod: The Reporting Period.

        """

        year = ReportingPeriod.date_year(date, session.entity)

        periods = session.scalars(
            select(ReportingPeriod)
            .where(ReportingPeriod.calendar_year == year)
            .where(ReportingPeriod.entity_id == session.entity.id)
        )

        try:
            return next(periods)
        except StopIteration as exc:
            raise MissingReportingPeriodError(session.entity, year) from exc

    def validate(self, session) -> None:
        """
        Validates the Reporting Period properties.

        Args:
            session (Session): The accounting session to which the ReportingPeriod belongs.

        Raises:
            DuplicateReportingPeriodError: If there already exists a Reporting Period
                for the same calendar year.
            MultipleOpenPeriodsError: If there already exists a Reporting Period
                in the OPEN status.

        Returns:
            None
        """

        if self.id is None:
            if (
                session.query(ReportingPeriod)
                .filter(ReportingPeriod.entity_id == self.entity_id)
                .filter(ReportingPeriod.calendar_year == self.calendar_year)
                .with_entities(func.count())  # pylint: disable=not-callable
                .execution_options(ignore_isolation=True)
                .scalar()
            ) > 0:
                raise DuplicateReportingPeriodError

            if (
                session.query(ReportingPeriod)
                .filter(ReportingPeriod.entity_id == self.entity_id)
                .filter(ReportingPeriod.status == ReportingPeriod.Status.OPEN)
                .with_entities(func.count())  # pylint: disable=not-callable
                .execution_options(ignore_isolation=True)
                .scalar()
            ) > 0 and self.status == ReportingPeriod.Status.OPEN:
                raise MultipleOpenPeriodsError

    def interval(self, date: datetime = None) -> dict:
        """
        Returns the start and end dates of the Reporting Period.

        Args:
            session (Session): The accounting session to which the Reporting Period
                 belongs.
            date (datetime): The date for whose Reporting Period's interval is to
                be found.

        Raises:
            MissingReportingPeriodError: If there no Reporting Period exists for the
                given date.


        Returns:
            ReportingPeriod: The Reporting Period.

        """
        year = (
            ReportingPeriod.date_year(date, self.entity) if date else self.calendar_year
        )
        start = datetime(
            year,
            self.entity.year_start,  # pylint: disable=no-member
            1,
            0,
            0,
            0,
        )

        return {
            "start": start,
            "end": start + relativedelta(years=1) - relativedelta(seconds=1),
        }
