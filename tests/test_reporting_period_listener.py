"""Moving the current Reporting Period does not commit the caller's work."""

from datetime import datetime

from sqlalchemy import select

from python_accounting.models import Account, Currency, ReportingPeriod


def _years(session, entity) -> list:
    return [
        period.calendar_year
        for period in session.scalars(
            select(ReportingPeriod)
            .where(ReportingPeriod.entity_id == entity.id)
            .order_by(ReportingPeriod.calendar_year)
            .execution_options(ignore_isolation=True)
        ).all()
    ]


def test_rollback_undoes_a_new_reporting_period(session, entity, currency, freeze_today):
    """When the year changes, the new Reporting Period is part of the caller's unit of work."""
    year = datetime.today().year
    assert _years(session, entity) == [year]

    freeze_today(year + 1, 3, 1)
    session.add(
        Account(
            name="Bank",
            account_type=Account.AccountType.BANK,
            currency_id=currency.id,
            entity_id=entity.id,
        )
    )
    assert _years(session, entity) == [year, year + 1]

    session.rollback()

    assert _years(session, entity) == [year]
    assert session.scalars(select(Account)).all() == []


def test_work_before_the_new_period_is_not_committed(session, entity, freeze_today):
    """Changes made before the period moved are not committed by the listener."""
    year = datetime.today().year
    session.add(Currency(name="Euro", code="EUR", entity_id=entity.id))
    session.flush()

    freeze_today(year + 1, 3, 1)
    session.add(Currency(name="Pound", code="GBP", entity_id=entity.id))
    session.rollback()

    codes = session.scalars(
        select(Currency.code).execution_options(ignore_isolation=True)
    ).all()
    assert "EUR" not in codes and "GBP" not in codes
