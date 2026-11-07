"""The precision of amount columns is configurable, and defaults to the existing schema."""

import re
import subprocess
import sys

import pytest

from python_accounting.models import Ledger, LineItem, Transaction, Balance, Assignment, Tax

SCRIPT = """
from python_accounting.config import config
config.database["amount_precision"] = {precision}
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from python_accounting.models import Ledger, LineItem, Transaction, Balance, Assignment, Tax
for column in (Ledger.amount, LineItem.amount, LineItem.quantity,
               Transaction.main_account_amount, Balance.amount, Assignment.amount):
    print(column.type.precision, column.type.scale)
print("tax", Tax.rate.type.precision)
print(CreateTable(Ledger.__table__).compile(dialect=postgresql.dialect()))
"""


def _run(precision) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", SCRIPT.format(precision=precision)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_default_precision_is_unchanged():
    """Without configuration the amount columns keep 13 digits with 4 decimals."""
    for column in (
        Ledger.amount,
        LineItem.amount,
        LineItem.quantity,
        Transaction.main_account_amount,
        Balance.amount,
        Assignment.amount,
    ):
        assert (column.type.precision, column.type.scale) == (13, 4)


def test_configured_precision_applies_to_amounts():
    """A precision set before the models are imported applies to every amount column."""
    result = _run(28)
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[:6] == ["28 4"] * 6
    assert lines[6] == "tax 13"  # a rate, not an amount
    assert re.search(r"\bamount (NUMERIC|DECIMAL)\(28, 4\)", result.stdout)


@pytest.mark.parametrize("precision", ["'28'", 4, 39, True])
def test_invalid_precision_is_refused(precision):
    """A precision that is not a whole number from 5 to 38 is refused when the models load."""
    result = _run(precision)
    assert result.returncode != 0
    assert "amount_precision" in result.stderr
