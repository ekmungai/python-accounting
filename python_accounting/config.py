# config.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents the configuration for python accounting.

"""
import toml


class Config:
    """Python Accounting configuration class"""

    testing: dict
    accounts: dict
    transactions: dict
    database: dict
    hashing: dict
    reports: dict
    dates: dict

    def __init__(self, config_file="config.toml") -> None:
        with open(config_file, "r", -1, "UTF-8") as f:
            configuration = toml.load(f)
            for k, v in configuration.items():
                setattr(self, k, v)


config = Config()
