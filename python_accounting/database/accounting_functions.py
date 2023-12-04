from datetime import datetime
from sqlalchemy import event, orm, and_, select, func
from python_accounting.models import Entity, Recyclable, ReportingPeriod


class AccountingFunctionsMixin:
    """This class provides accounting specific functionality to the generic sqlachemy session"""

    def _year_period(self, year) -> orm.Mapped["ReportingPeriod"] | None:
        """Get the reporting period for the given year"""

        return self.scalars(
            select(ReportingPeriod)
            .where(ReportingPeriod.calendar_year == year)
            .where(ReportingPeriod.entity_id == self.entity.id)
            .execution_options(ignore_isolation=True)
        ).first()

    def _set_reporting_period(session) -> None:
        """Set the session entity's current reporting period"""
        year = datetime.today().year
        existing = session._year_period(year)

        if existing:
            session.entity.reporting_period_id = existing.id
        else:
            past_periods = (
                session.query(ReportingPeriod)
                .filter(ReportingPeriod.entity_id == session.entity.id)
                .with_entities(func.count())
                .execution_options(ignore_isolation=True)
                .scalar()
            )

            session.add(
                ReportingPeriod(
                    calendar_year=year,
                    period_count=past_periods + 1,
                    entity_id=session.entity.id,
                )
            )
            session.flush()

            session.entity.reporting_period = session._year_period(year)
        session.commit()
