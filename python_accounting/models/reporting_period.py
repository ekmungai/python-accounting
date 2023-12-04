from datetime import datetime
from dateutil.relativedelta import relativedelta
from enum import Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, UniqueConstraint, func, select
from python_accounting.mixins import IsolatingMixin
from python_accounting.exceptions import (
    DuplicateReportingPeriodError,
    MissingReportingPeriodError,
)
from .recyclable import Recyclable


class ReportingPeriod(IsolatingMixin, Recyclable):
    """Represents a financial year for the Reporting Entity"""

    __tablename__ = "reporting_period"
    __table_args__ = (UniqueConstraint("calendar_year", "entity_id"),)

    class Status(Enum):
        """Reporting Period status"""

        OPEN = 0
        ADJUSTING = 1
        CLSOED = 2

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
    def period_span(cls, date: datetime = None, entity=None) -> dict:
        """Returns the start and end dates of the reporting period for the given date"""
        today = datetime.today()

        start = (
            datetime(
                ReportingPeriod.date_year(date, entity), entity.year_start, 1, 0, 0, 0
            )
            if entity
            else datetime(today.year, 1, 1, 0, 0, 0)
        )

        return dict(
            period_start=start,
            period_end=start + relativedelta(years=1) - relativedelta(seconds=1),
        )

    @classmethod
    def get_period(cls, date: datetime, entity, session) -> int:
        """Returns the reporting period for the given date"""

        year = ReportingPeriod.date_year(date, entity)

        period = session.scalars(
            select(ReportingPeriod)
            .where(ReportingPeriod.calendar_year == year)
            .where(ReportingPeriod.entity_id == entity.id)
        )

        try:
            return next(period)
        except StopIteration:
            raise MissingReportingPeriodError(entity, year)

    def validate(self, session):
        """Validate the reporting period properties"""

        if (
            session.query(ReportingPeriod)
            .filter(ReportingPeriod.entity_id == self.entity_id)
            .filter(ReportingPeriod.calendar_year == self.calendar_year)
            .with_entities(func.count())
            .execution_options(ignore_isolation=True)
            .scalar()
        ) > 0:
            raise DuplicateReportingPeriodError
