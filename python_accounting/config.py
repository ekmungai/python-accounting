# config.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
This module provides the configuration for python accounting. Its properties are populated from 
`config.toml <https://github.com/ekmungai/python-accounting/blob/main/config.toml>`__ by default and 
should be adequate for most settings, but there are a few methods for overriding the database, 
hashing and dates configurations. For more extensive custom configurations, you can initialize 
the class with a custom config.tml file.

"""
import os
import pathlib
import toml


class Config:
    """
    Python Accounting configuration class.
    """

    database: dict
    """
    The database configuration.
    ::
        {
            url (str): The database connection string. Defaults to 'sqlite://'.
            echo (bool): Whether to output the SqlAlchemy generated queries to the console.
            Defaults to false.
            include_deleted (bool): Whether to include soft deleted records in query results.
            Defaults to false. 
            ignore_isolation (bool): Whether to include records from all entities in query
            results.
            Defaults to false.
        }
    """
    hashing: dict
    """
    Configuration for hashing Ledger records to guard against direct database tampering.
    ::
        {
            salt (str): The initial value for the ledger hashing. Defaults to 'hashing salt'.
            algorithm (str): The Algorithm to use for encoding the hashes. Defaults to 'sha256'.
        }
    """
    dates: dict
    """
    Configuration for formatting dates in reports.
    ::
        {
            short (str): The format for short dates. Defaults to '%Y-%m-%d'.
            long (str): The format for long dates. Defaults to '%d, %b %Y'.
        }
    """
    accounts: dict
    """
    Account Types, Codes and Financial Report section membership Configuration
    ::
        {
            types (dict): The Account Types as defined by GAAP/IFRS:
            label (str): The human readable name of the Account Type.
            account_code (int): The starting point for the genaration of Account Codes for
            Accounts of the type.
            purchasables (list): Account types that can be used in purchasing Transations. 
        }
    """
    transactions: dict
    """
    Transaction Types, Number Prefixes and clearable/assignable Configuration
    ::
        {
            types (`dict`): The Transaction Types as defined by GAAP/IFRS
            label (`str`): The human readable name of the Transaction Type.
            transaction_no_prefix (`int`): The code to be inserted at the beginningof the
            Transaction's type's sequentially generated transaction number.
            clearables (`list`): Transaction types that can cleared by assignable Transactions.  
            assignables (`list`): Transaction types that can user to cleared (have assigned
            to them) clearable Transactions.
        }  
    """
    reports: dict
    """
    Configuration for Financial Reports.
    ::
        {
            indent_length (`int`): Number of spaces to indent report sections. Defaults to 4.
            result_length (`int`): Number of characters to underline report results. Defaults
            to 15.
            aging_schedule_brackets (`dict`): The labels and max age in days for aging schedule
            brackets.
        }  
    """

    def __init__(self, config_file) -> None:
        with open(config_file, "r", -1, "UTF-8") as f:
            configuration = toml.load(f)
            for k, v in configuration.items():
                setattr(self, k, v)

    def configure_database(
        self, url, echo=False, include_deleted=False, ignore_isolation=False
    ) -> None:
        # pylint: disable = line-too-long
        """
        Configures the database.

        Args:
            url (str): The database connection string.
            echo (bool): Whether to output the SqlAlchemy generated queries to the console. Defaults to false.
            include_deleted (bool): Whether to include soft deleted records in query results. Defaults to false.
            ignore_isolation (bool): Whether to include records from all entities in query results. Defaults to false.
        """
        # pylint: enable = line-too-long
        self.database["url"] = url
        self.database["echo"] = echo
        self.database["include_deleted"] = include_deleted
        self.database["ignore_isolation"] = ignore_isolation

    def configure_hashing(self, salt="hashing salt", algorithm="sha256") -> None:
        """
        Configures hashing.

        Args:
            salt (str): The initial value for the ledger hashing. Defaults to 'hashing salt'.
            algorithm (str): The Algorithm to use for encoding the hashes. Defaults to 'sha256'.
        """
        self.hashing["salt"] = salt
        self.hashing["algorithm"] = algorithm

    def configure_dates(self, short="%Y-%m-%d", long="%d, %b %Y") -> None:
        """
        Configures dates.

        Args:
            short (str): The format for short dates. Defaults to '%Y-%m-%d'.
            long (str): The format for long dates. Defaults to '%d, %b %Y'.
        """
        self.hashing["short"] = short
        self.hashing["long"] = long


default_configuration = os.path.join(
    pathlib.Path(__file__).parent.parent.resolve(), "config.toml"
)
config = Config(config_file=default_configuration)
"""The default configuration"""
