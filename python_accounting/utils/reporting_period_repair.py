# utils/reporting_period_repair.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Finds and repairs what earlier versions left behind for Entities whose year does not
start in January.

Earlier versions took the current Reporting Period from the calendar year, so from
January until the month before year_start they opened the next year's period before
it began and moved the running period to Adjusting. Balances take the current period
when they are saved, so those saved in those months landed a year late: missing from
the reports of their own year, and appearing in the next. Transactions were not
affected, as they resolve their period from their own date.

That leaves two fingerprints: a period that has not begun, and a Balance created
before year_start whose period is labelled with the calendar year it was created in.
A period that has not begun can only hold Balances misattached to it. The other
fingerprint is weaker, as created_at holds the time the application started rather
than the time the Balance was saved, so the findings need reviewing before they are
applied.

"""
from dataclasses import dataclass, field
from sqlalchemy import delete, select, update
from python_accounting.models import Balance, Entity, Recyclable, ReportingPeriod

CLOSED_PERIOD = "Reporting Period is closed"
"""(str): Why a finding cannot be repaired: one of its periods is closed."""
MISSING_PERIOD = "Reporting Period does not exist"
"""(str): Why a finding cannot be repaired: it has no period to move to."""


@dataclass
class PrematurePeriod:
    """A Reporting Period opened before it began."""

    period: ReportingPeriod
    """(ReportingPeriod): The period that has not begun."""
    previous: ReportingPeriod | None
    """(`ReportingPeriod`, optional): The running period. If absent, the premature
    period takes its place."""
    blocked: str | None
    """(`str`, optional): Why the period cannot be repaired."""


@dataclass
class MisattachedBalance:
    """A Balance attached to the Reporting Period after the one it belongs to."""

    balance: Balance
    """(Balance): The misattached Balance."""
    period: ReportingPeriod
    """(ReportingPeriod): The period the Balance is attached to."""
    target: ReportingPeriod | None
    """(`ReportingPeriod`, optional): The period the Balance belongs to."""
    blocked: str | None
    """(`str`, optional): Why the Balance cannot be moved."""


@dataclass
class Findings:
    """The Reporting Periods and Balances that need repairing."""

    periods: list = field(default_factory=list)
    """(`list` of PrematurePeriod): The periods opened before they began."""
    balances: list = field(default_factory=list)
    """(`list` of MisattachedBalance): The Balances attached to the wrong period."""


def _blocked(*periods: ReportingPeriod) -> str | None:
    if any(p.status == ReportingPeriod.Status.CLOSED for p in periods):
        return CLOSED_PERIOD
    return None


def _is_late(balance: Balance, period: ReportingPeriod, year_start: int) -> bool:
    return (
        balance.created_at.month < year_start
        and balance.created_at.year == period.calendar_year
    )


def find(session) -> Findings:
    """
    Finds what needs repairing for the session's Entity, without changing anything.

    Args:
        session (Session): The accounting session of the Entity.

    Returns:
        Findings: The Reporting Periods and Balances that need repairing.
    """
    entity = session.entity
    findings = Findings()

    # A year starting in January has no months before it for the fault to occur in
    if entity.year_start == 1:
        return findings

    periods = session.scalars(select(ReportingPeriod)).all()
    by_year = {p.calendar_year: p for p in periods}
    by_id = {p.id: p for p in periods}

    year = ReportingPeriod.date_year(entity=entity)
    premature = by_year.get(year + 1)
    if premature:
        previous = by_year.get(year)
        findings.periods.append(
            PrematurePeriod(
                premature,
                previous,
                _blocked(premature, *([previous] if previous else [])),
            )
        )

    balances = session.scalars(
        select(Balance).execution_options(include_deleted=True)
    ).all()
    for balance in balances:
        period = by_id[balance.reporting_period_id]
        target = by_year.get(period.calendar_year - 1)

        # Without a running period to move to, the Balance stays with the period
        if period is premature and target is None:
            continue

        if period is premature or _is_late(balance, period, entity.year_start):
            findings.balances.append(
                MisattachedBalance(
                    balance,
                    period,
                    target,
                    _blocked(period, target) if target else MISSING_PERIOD,
                )
            )

    return findings


def _attach(connection, balance: Balance, current_year: int, values: dict) -> None:
    # The default transaction number carries the year of the period
    prefix = f"{balance.account_id}{balance.currency.code}"
    if balance.transaction_no == f"{prefix}{current_year}":
        values = {**values, "transaction_no": f"{prefix}{current_year - 1}"}

    # Core rather than the ORM, as validation attaches Balances to the current period
    table = Balance.__table__
    connection.execute(
        update(table).where(table.c.id == balance.id).values(values)
    )


def _replace(session, connection, period: ReportingPeriod, previous) -> None:
    entity_id = session.entity.id
    periods = ReportingPeriod.__table__
    connection.execute(
        update(Entity.__table__)
        .where(Entity.__table__.c.id == entity_id)
        .values(reporting_period_id=previous.id)
    )
    connection.execute(
        update(periods)
        .where(periods.c.id == previous.id)
        .values(status=ReportingPeriod.Status.OPEN)
    )
    # Destroyed rather than recycled, as its period count will be used again
    connection.execute(delete(periods).where(periods.c.id == period.id))
    connection.execute(
        delete(Recyclable.__table__).where(Recyclable.__table__.c.id == period.id)
    )
    session.expunge(period)


def repair(session, findings: Findings) -> int:
    """
    Repairs the findings, leaving those that are blocked, in one database transaction.

    Args:
        session (Session): The accounting session of the Entity.
        findings (Findings): The findings to repair.

    Returns:
        int: The number of findings repaired.
    """
    balances = [f for f in findings.balances if f.blocked is None]
    periods = [f for f in findings.periods if f.blocked is None]

    try:
        connection = session.connection()

        for finding in balances:
            _attach(
                connection,
                finding.balance,
                finding.period.calendar_year,
                {"reporting_period_id": finding.target.id},
            )

        for finding in periods:
            if finding.previous:
                _replace(session, connection, finding.period, finding.previous)
                continue

            year = finding.period.calendar_year
            connection.execute(
                update(ReportingPeriod.__table__)
                .where(ReportingPeriod.__table__.c.id == finding.period.id)
                .values(calendar_year=year - 1)
            )
            for balance in session.scalars(
                select(Balance)
                .where(Balance.reporting_period_id == finding.period.id)
                .execution_options(include_deleted=True)
            ).all():
                _attach(connection, balance, year, {})

        session.commit()
    except Exception:
        session.rollback()
        raise

    return len(balances) + len(periods)
