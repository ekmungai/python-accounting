# database/database_init.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Database initialization based on the engine and PythonAccounting models.
"""
from python_accounting.database.engine import engine
from python_accounting import models


def database_init() -> None:
    """
    Initializes the database by setting up all tables that do not currently exist.

    Returns:
        None
    """

    models.Base.metadata.create_all(engine)
