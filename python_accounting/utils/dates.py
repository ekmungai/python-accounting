# utils/dates.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Provides accounting specific date utilities.

"""
from datetime import datetime
from python_accounting.models.reporting_period import ReportingPeriod


def get_dates(session, start_date: datetime = None, end_date: datetime = None) -> tuple:
    """
    Returns the dates of a report given the inputs provided.

    Args:
        session (Session): The accounting session of the report.
        start_date (`datetime`, optional): The start date. Defaults to the start of
            the Reporting Period containing the end date.
        end_date (`datetime`, optional): The end date. Defaults to today.

    Raises:
        MissingReportingPeriodError: If no Reporting Period contains the end date.

    Returns:
        tuple: The start date, the end of the end date, the start of its Reporting
        Period and the id of that Reporting Period.
    """
    end_date = datetime.today() if not end_date else end_date
    period = ReportingPeriod.get_period(session, end_date)
    period_start = period.interval()["start"]
    start_date = period_start if not start_date else start_date

    return (
        start_date,
        end_date.replace(hour=23, minute=59, second=59, microsecond=999999),
        period_start,
        period.id,
    )
