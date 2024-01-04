from datetime import datetime
from python_accounting.models.reporting_period import ReportingPeriod


def get_dates(session, start_date: datetime = None, end_date: datetime = None) -> tuple:
    """Returns the start, end and period start dates given the inputs provided"""
    end_date = datetime.today() if not end_date else end_date
    period = ReportingPeriod.get_period(
        session, datetime(end_date.year, session.entity.year_start, 1, 0, 0, 0)
    )
    period_start = period.interval()["start"]
    start_date = period_start if not start_date else start_date

    return (
        start_date,
        end_date.replace(hour=23, minute=59, second=59, microsecond=999999),
        period_start,
        period.id,
    )
