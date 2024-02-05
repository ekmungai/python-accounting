# database/database_init.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Database engine configuration.

"""

from sqlalchemy import create_engine
from python_accounting.config import config


database = config.database
engine = create_engine(database["url"], echo=database["echo"]).execution_options(
    include_deleted=database["include_deleted"],
    ignore_isolation=database["ignore_isolation"],
)
