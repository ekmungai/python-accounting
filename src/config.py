# config.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
This module provides the configuration for python accounting. Its properties are populated from the
config.toml by default and should be adequate for most settings (except maybe the datatabse 
configuration), but being a plain python object any of the attributes may be overriden by
assingment at any point. For more extensive custom configurations, you can initialize the
class with a custom config.tml file.

"""
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
            url (str): The database connection string.
            echo (bool): Whether to output the SqlAlchemy generated queries to the console. 
            include_deleted (bool): Whether to include soft deleted records in query results. 
            echo (bool): Whether to include records from all entities in query results. 
        }
    """
    hashing: dict
    """
    Configuration for hashing Ledger records to guard against direct database tampering.
    ::
        {
            salt (str): The initial salt for .
            echo (bool): Whether to output the SqlAlchemy generated queries to the console. 
            include_deleted (bool): Whether to include soft deleted records in query results. 
            echo (bool): Whether to include records from all entities in query results. 
        }
    """
    accounts: dict
    dates: dict
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
            transaction_no_prefix (`int`): The code to be inserted at the beginning
             of the Transaction's type's sequentially generated transaction number.
            clearables (`list`): Transaction types that can cleared by assignable Transactions.  
            assignables (`list`): Transaction types that can user to cleared (have assigned
             to them) clearable Transactions.
        }  
    """
    reports: dict

    def __init__(self, config_file="config.toml") -> None:
        with open(config_file, "r", -1, "UTF-8") as f:
            configuration = toml.load(f)
            for k, v in configuration.items():
                setattr(self, k, v)


config = Config()
"""The default configuration"""
