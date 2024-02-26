import pytest
from datetime import datetime
from sqlalchemy import select
from python_accounting.models import ReportingPeriod, Entity
from python_accounting.exceptions import (
    DuplicateReportingPeriodError,
    MissingReportingPeriodError,
)


def test_reporting_period_entity(session, entity):
    """Tests the relationship between a reporting period and its associated entity"""
    reporting_period = ReportingPeriod(
        calendar_year=datetime.today().year + 1,
        period_count=2,
        status=ReportingPeriod.Status.ADJUSTING,
        entity_id=entity.id,
    )
    session.add(reporting_period)
    session.commit()

    reporting_period = session.get(ReportingPeriod, reporting_period.id)
    assert reporting_period.entity.name == "Test Entity"


def test_reporting_period_validation(session, entity):
    """Tests the validation of reporting period objects"""
    with pytest.raises(DuplicateReportingPeriodError):
        session.add(
            ReportingPeriod(
                calendar_year=datetime.today().year, period_count=1, entity_id=entity.id
            )
        )


def test_reporting_period_isolation(session, entity):
    """Tests the isolation of reporting period objects by entity"""

    year = datetime.today().year
    entity2 = Entity(name="Test Entity Two")
    session.add(entity2)
    session.flush()
    entity2 = session.get(Entity, entity2.id)

    session.add_all(
        [
            ReportingPeriod(
                calendar_year=year - 1,
                period_count=2,
                entity_id=entity.id,
                status=ReportingPeriod.Status.ADJUSTING,
            ),
            ReportingPeriod(
                calendar_year=year,
                period_count=3,
                entity_id=entity2.id,
            ),
        ]
    )
    session.commit()

    reporting_periods = session.scalars(select(ReportingPeriod)).all()

    assert len(reporting_periods) == 2
    assert reporting_periods[0].calendar_year == year
    assert reporting_periods[0].period_count == 1
    assert reporting_periods[0].entity.name == "Test Entity"

    reporting_period2 = session.get(ReportingPeriod, 3)
    assert reporting_period2 == None

    session.entity = entity2
    reporting_periods = session.scalars(select(ReportingPeriod)).all()

    assert len(reporting_periods) == 1
    assert reporting_periods[0].calendar_year == year
    assert reporting_periods[0].period_count == 3
    assert reporting_periods[0].entity.name == "Test Entity Two"

    reporting_period1 = session.get(ReportingPeriod, 1)
    assert reporting_period1 == None


def test_reporting_period_recycling(session, entity):
    """Tests the deleting, restoring and destroying functions of the reporting_period model"""

    reporting_period = ReportingPeriod(
        calendar_year=datetime.today().year - 1,
        status=ReportingPeriod.Status.ADJUSTING,
        period_count=2,
        entity_id=entity.id,
    )
    session.add(reporting_period)
    session.flush()

    reporting_period_id = reporting_period.id

    session.delete(reporting_period)

    reporting_period = session.get(ReportingPeriod, reporting_period_id)
    assert reporting_period == None

    reporting_period = session.get(
        ReportingPeriod, reporting_period_id, include_deleted=True
    )
    assert reporting_period != None
    session.restore(reporting_period)

    reporting_period = session.get(ReportingPeriod, reporting_period_id)
    assert reporting_period != None

    session.destroy(reporting_period)

    reporting_period = session.get(ReportingPeriod, reporting_period_id)
    assert reporting_period == None

    reporting_period = session.get(
        ReportingPeriod, reporting_period_id, include_deleted=True
    )
    assert reporting_period != None
    session.restore(reporting_period)  # destroyed models canot be restored

    reporting_period = session.get(ReportingPeriod, reporting_period_id)
    assert reporting_period == None


def test_reporting_period_dates(session, entity):
    """Tests the calculation of reporting_period start and end dates"""

    assert ReportingPeriod.date_year() == datetime.today().year
    assert (
        ReportingPeriod.date_year(datetime.strptime("2025-06-03", "%Y-%m-%d"), entity)
        == 2025
    )

    new_reporting_period = ReportingPeriod(
        calendar_year=2025,
        period_count=2,
        entity_id=entity.id,
    )
    session.add(new_reporting_period)
    session.commit()
    period_interval = new_reporting_period.interval(
        datetime.strptime("2025-06-03", "%Y-%m-%d")
    )
    assert period_interval["start"] == datetime(2025, 1, 1, 0, 0, 0)
    assert period_interval["end"] == datetime(2025, 12, 31, 23, 59, 59)

    entity.year_start = 4

    assert (
        ReportingPeriod.date_year(datetime.strptime("2025-03-03", "%Y-%m-%d"), entity)
        == 2024
    )

    period_interval = new_reporting_period.interval(
        datetime.strptime("2025-03-03", "%Y-%m-%d")
    )
    assert period_interval["start"] == datetime(2024, 4, 1, 0, 0, 0)
    assert period_interval["end"] == datetime(2025, 3, 31, 23, 59, 59)


def test_reporting_period_from_date(session, entity):
    """Tests the retrieval of the reporting_period for a given date"""

    assert (
        ReportingPeriod.get_period(session, datetime.today()) == entity.reporting_period
    )
    with pytest.raises(MissingReportingPeriodError):
        ReportingPeriod.get_period(session, datetime.strptime("2025-03-03", "%Y-%m-%d"))

    new_reporting_period = ReportingPeriod(
        calendar_year=2025,
        period_count=2,
        entity_id=entity.id,
    )
    session.add(new_reporting_period)
    session.commit()

    assert (
        ReportingPeriod.get_period(session, datetime.strptime("2025-03-03", "%Y-%m-%d"))
        == new_reporting_period
    )
