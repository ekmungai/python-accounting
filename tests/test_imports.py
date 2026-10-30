import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "python_accounting.models",
        "python_accounting.reports",
        "python_accounting.transactions",
    ],
)
def test_package_can_be_imported_first(module):
    """No package depends on another having been imported before it"""

    subprocess.run([sys.executable, "-c", f"import {module}"], check=True)
