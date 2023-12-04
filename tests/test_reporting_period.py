import pytest
from datetime import datetime
from .conftest import engine, entity, session
from sqlalchemy import select
import python_accounting.models as models
from python_accounting.exceptions import (
    DuplicateReportingPeriodError,
    MissingReportingPeriodError,
)


def test_reporting_period_entity(entity, session):
    """Tests the relationship between a reporting period and its associated entity"""
    reporting_period = models.ReportingPeriod(
        calendar_year=datetime.today().year + 1, period_count=2, entity_id=entity.id
    )
    session.add(reporting_period)
    session.commit()

    reporting_period = session.get(models.ReportingPeriod, reporting_period.id)
    assert reporting_period.entity.name == "Test Entity"


def test_reporting_period_validation(session, entity):
    """Tests the validation of reporting period objects"""
    with pytest.raises(DuplicateReportingPeriodError):
        session.add(
            models.ReportingPeriod(
                calendar_year=datetime.today().year, period_count=1, entity_id=entity.id
            )
        )


def test_reporting_period_isolation(session, entity):
    """Tests the isolation of reporting period objects by entity"""

    year = datetime.today().year
    entity2 = models.Entity(name="Test Entity Two")
    session.add(entity2)
    session.flush()
    entity2 = session.get(models.Entity, entity2.id)

    session.add_all(
        [
            models.ReportingPeriod(
                calendar_year=year - 1, period_count=1, entity_id=entity.id
            ),
            models.ReportingPeriod(
                calendar_year=year,
                period_count=2,
                entity_id=entity2.id,
            ),
        ]
    )
    session.commit()

    reporting_periods = session.scalars(select(models.ReportingPeriod)).all()

    assert len(reporting_periods) == 2
    assert reporting_periods[0].calendar_year == year
    assert reporting_periods[0].period_count == 1
    assert reporting_periods[0].entity.name == "Test Entity"

    reporting_period2 = session.get(models.ReportingPeriod, 3)
    assert reporting_period2 == None

    session.entity = entity2
    reporting_periods = session.scalars(select(models.ReportingPeriod)).all()

    assert len(reporting_periods) == 1
    assert reporting_periods[0].calendar_year == year
    assert reporting_periods[0].period_count == 2
    assert reporting_periods[0].entity.name == "Test Entity Two"

    reporting_period1 = session.get(models.ReportingPeriod, 1)
    assert reporting_period1 == None


def test_reporting_period_recycling(session, entity):
    """Tests the deleting, restoring and destroying functions of the reporting_period model"""

    reporting_period = models.ReportingPeriod(
        calendar_year=datetime.today().year - 1, period_count=1, entity_id=entity.id
    )
    session.add(reporting_period)
    session.flush()

    reporting_period_id = reporting_period.id

    session.delete(reporting_period)

    reporting_period = session.get(models.ReportingPeriod, reporting_period_id)
    assert reporting_period == None

    reporting_period = session.get(
        models.ReportingPeriod, reporting_period_id, include_deleted=True
    )
    assert reporting_period != None
    session.restore(reporting_period)

    reporting_period = session.get(models.ReportingPeriod, reporting_period_id)
    assert reporting_period != None

    session.destroy(reporting_period)

    reporting_period = session.get(models.ReportingPeriod, reporting_period_id)
    assert reporting_period == None

    reporting_period = session.get(
        models.ReportingPeriod, reporting_period_id, include_deleted=True
    )
    assert reporting_period != None
    session.restore(reporting_period)  # destroyed models canot be restored

    reporting_period = session.get(models.ReportingPeriod, reporting_period_id)
    assert reporting_period == None


def test_reporting_period_dates(entity):
    """Tests the calculation of reporting_period start and end dates"""

    assert models.ReportingPeriod.date_year() == datetime.today().year
    assert (
        models.ReportingPeriod.date_year(
            datetime.strptime("2025-06-03", "%Y-%m-%d"), entity
        )
        == 2025
    )

    period_span = models.ReportingPeriod.period_span(
        datetime.strptime("2025-06-03", "%Y-%m-%d"), entity
    )
    assert period_span["period_start"] == datetime(2025, 1, 1, 0, 0, 0)
    assert period_span["period_end"] == datetime(2025, 12, 31, 23, 59, 59)

    entity.year_start = 4

    assert (
        models.ReportingPeriod.date_year(
            datetime.strptime("2025-03-03", "%Y-%m-%d"), entity
        )
        == 2024
    )
    period_span = models.ReportingPeriod.period_span(
        datetime.strptime("2025-03-03", "%Y-%m-%d"), entity
    )
    assert period_span["period_start"] == datetime(2024, 4, 1, 0, 0, 0)
    assert period_span["period_end"] == datetime(2025, 3, 31, 23, 59, 59)


def test_reporting_period_from_date(session, entity):
    """Tests the retrieval of the reporting_period for a given date"""

    with pytest.raises(MissingReportingPeriodError):
        models.ReportingPeriod.get_period(
            datetime.strptime("2025-03-03", "%Y-%m-%d"), entity, session
        )

    models.ReportingPeriod.get_period(
        datetime.today(), entity, session
    ) == entity.reporting_period
