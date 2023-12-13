from datetime import datetime
from dateutil.relativedelta import relativedelta
from enum import Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, UniqueConstraint, func, select
from python_accounting.mixins import IsolatingMixin
from python_accounting.exceptions import (
    DuplicateReportingPeriodError,
    MissingReportingPeriodError,
    MultipleOpenPeriodsError,
)
from .recyclable import Recyclable


class ReportingPeriod(IsolatingMixin, Recyclable):
    """Represents a financial year for the Reporting Entity"""

    __tablename__ = "reporting_period"
    __table_args__ = (
        UniqueConstraint("calendar_year", "entity_id"),
        UniqueConstraint("period_count", "entity_id"),
    )

    class Status(Enum):
        """Reporting Period status"""

        OPEN = 0
        ADJUSTING = 1
        CLOSED = 2

    __mapper_args__ = {"polymorphic_identity": "ReportingPeriod"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    calendar_year: Mapped[int] = mapped_column()
    period_count: Mapped[int] = mapped_column()
    status: Mapped[Status] = mapped_column(default=Status.OPEN)

    def __repr__(self) -> str:
        return f"{self.calendar_year} <Period {self.period_count}>"

    @classmethod
    def date_year(cls, date: datetime = None, entity=None) -> int:
        """Returns the calendar year for the given date"""

        today = datetime.today()
        if not entity:
            return today.year

        month, year = (date.month, date.year) if date else (today.month, today.year)
        return year if month >= entity.year_start else year - 1

    @classmethod
    def get_period(cls, date: datetime, session) -> int:
        """Returns the reporting period for the given date"""

        year = ReportingPeriod.date_year(date, session.entity)

        periods = session.scalars(
            select(ReportingPeriod)
            .where(ReportingPeriod.calendar_year == year)
            .where(ReportingPeriod.entity_id == session.entity.id)
        )

        try:
            return next(periods)
        except StopIteration:
            raise MissingReportingPeriodError(session.entity, year)

    def validate(self, session):
        """Validate the reporting period properties"""

        if self.id is None:
            if (
                session.query(ReportingPeriod)
                .filter(ReportingPeriod.entity_id == self.entity_id)
                .filter(ReportingPeriod.calendar_year == self.calendar_year)
                .with_entities(func.count())
                .execution_options(ignore_isolation=True)
                .scalar()
            ) > 0:
                raise DuplicateReportingPeriodError

            if (
                session.query(ReportingPeriod)
                .filter(ReportingPeriod.entity_id == self.entity_id)
                .filter(ReportingPeriod.status == ReportingPeriod.Status.OPEN)
                .with_entities(func.count())
                .execution_options(ignore_isolation=True)
                .scalar()
            ) > 0 and self.status == ReportingPeriod.Status.OPEN:
                raise MultipleOpenPeriodsError

    def interval(self, date: datetime = None) -> dict:
        """Returns the start and end dates of the reporting period"""
        year = (
            ReportingPeriod.date_year(date, self.entity) if date else self.calendar_year
        )
        start = datetime(
            year,
            self.entity.year_start,
            1,
            0,
            0,
            0,
        )

        return dict(
            start=start,
            end=start + relativedelta(years=1) - relativedelta(seconds=1),
        )
