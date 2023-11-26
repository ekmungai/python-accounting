import sys


class AccountingExeption(Exception):
    """Base accounting exception"""

    message: str

    def __str__(self):
        return f"{self.message}"
