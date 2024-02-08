# config.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents the configuration for python accounting. Its properties are populated from the config.toml by default.

"""
import toml


class Config:
    """
    Python Accounting configuration class. The defaults settings are loaded from config.toml
    and should be adequate for most settings (except maybe the datatabse configuration), but
    being a plain python object any of the attributes may be overriden by assingment at any
    point.
    """

    testing: dict
    """
    Database configuration for running unit tests
    ::
        {
            url (str): The database connection string.
            echo (bool): Whether to output the SqlAlchemy generated queries to the console. 
        }
    """
    accounts: dict
    """
    Account Types, Codes and Financial Report section membership Configuration
    ::
        {
            types (dict): The Account Types as defined by GAAP/IFRS:
            label (str): The human readable name of the Account Type.
            account_code (int): The starting point for the genaration of Account Codes 
                for Accounts of the type.
            purchasables (list): Account types that can be used in purchasing Transations. 
        }
    """
    transactions: dict
    """
    Transaction Types, Number Prefixes and clearable/assignable Configuration::
        types (`dict`): The Transaction Types as defined by GAAP/IFRS
            label (`str`): The human readable name of the Transaction Type.
            transaction_no_prefix (`int`): The code to be inserted at the beginning 
            of the Transaction's type's sequentially generated transaction number.
        clearables (`list`): Transaction types that can cleared by assignable Transactions.  
        assignables (`list`): Transaction types that can user to cleared (have assigned to them) clearable Transactions.  
    """
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
