# database/accounting_functions.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
This mixin providses accounting specific functionality to the standard sqlachemy session.
"""

# pylint: disable=too-few-public-methods
from datetime import datetime
from sqlalchemy import orm, select, func
from python_accounting.models import ReportingPeriod


class AccountingFunctionsMixin:
    """
    Accounting functions class.

    """

    def _year_period(self, year: int) -> orm.Mapped["ReportingPeriod"]:
        return self.scalars(
            select(ReportingPeriod)
            .where(ReportingPeriod.calendar_year == year)
            .where(ReportingPeriod.entity_id == self.entity.id)
            .execution_options(ignore_isolation=True)
        ).first()

    def _set_reporting_period(self) -> None:
        year = datetime.today().year
        existing = self._year_period(year)

        if existing:
            self.entity.reporting_period_id = existing.id
        else:
            # transission the previous period to adjusting status if one exists
            previous_period = self._year_period(year - 1)
            if (
                previous_period
                and previous_period.status == ReportingPeriod.Status.OPEN
            ):
                previous_period.status = ReportingPeriod.Status.ADJUSTING
                self.add(previous_period)
                self.flush()

            past_periods = (
                self.query(ReportingPeriod)
                .filter(ReportingPeriod.entity_id == self.entity.id)
                .with_entities(func.count())  # pylint: disable=not-callable
                .execution_options(ignore_isolation=True)
                .scalar()
            )

            self.add(
                ReportingPeriod(
                    calendar_year=year,
                    period_count=past_periods + 1,
                    entity_id=self.entity.id,
                )
            )
            self.flush()

            self.entity.reporting_period = self._year_period(year)
        self.commit()
