import sys


class AccountingExeption(Exception):
    """Base accounting exception"""

    message: str

    def __str__(self) -> str:
        return f"{self.message}"
