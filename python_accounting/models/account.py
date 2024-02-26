# models/account.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents an Account, the basic unit of accounting that groups the transactions of an Entity.
"""
import warnings
from decimal import Decimal
from datetime import datetime
from strenum import StrEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship, aliased
from sqlalchemy import String, ForeignKey, Enum, func, inspect, select, or_, exc
from python_accounting.models.recyclable import Recyclable
from python_accounting.models.reporting_period import ReportingPeriod
from python_accounting.mixins import IsolatingMixin
from python_accounting.config import config
from python_accounting.exceptions import (
    InvalidCategoryAccountTypeError,
    InvalidAccountTypeError,
    HangingTransactionsError,
)
from python_accounting.utils.dates import get_dates

account_type_enum = StrEnum(
    "AccountType", {k: v["label"] for k, v in config.accounts["types"].items()}
)


class Account(IsolatingMixin, Recyclable):
    """Represents an account which groups related Transactions."""

    # Chart of Accounts types
    AccountType = account_type_enum
    """(StrEnum): Account Types as defined by IFRS and GAAP."""

    # Account Types that can be used in Purchasing Transactions
    purchasables = [
        account_type_enum[t] for t in config.accounts["purchasables"]["types"]
    ]
    """
    (`list` of `Account.AccountType`): A list of Account
    Types that can be used in purchasing Transactions.
    """

    __mapper_args__ = {"polymorphic_identity": "Account"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    """(int): The primary key of the Account database record."""
    name: Mapped[str] = mapped_column(String(255))
    """(str): The label of the Account."""
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    """(`str`, optional): A narration of the purpose of the Account."""
    account_code: Mapped[int] = mapped_column()
    """(int): A serially generated code based on the type of the Account."""
    account_type: Mapped[StrEnum] = mapped_column(Enum(AccountType))
    """(AccountType): The type of the Account."""
    currency_id: Mapped[int] = mapped_column(ForeignKey("currency.id"))
    """(int): The id of the Currency model associated with the Account."""
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"), nullable=True)
    """(`int`, optional): The id of the Category model to which the Account belongs."""

    # relationships
    currency: Mapped["Currency"] = relationship(foreign_keys=[currency_id])
    """(Currency): The Currency associated with the Account."""
    category: Mapped["Category"] = relationship(foreign_keys=[category_id])
    """(`Category`, optional): The Category to which the Account belongs."""

    def _get_account_code(self, session) -> int:
        current_count = (
            session.query(Account)
            .filter(Account.entity_id == self.entity_id)
            .filter(Account.account_type == self.account_type)
            .with_entities(func.count())  # pylint: disable=not-callable
            .scalar()
        )

        return (
            int(config.accounts["types"][self.account_type.name]["account_code"])
            + current_count
            + getattr(self, "session_index", 1)
        )

    def __repr__(self) -> str:
        return f"{self.account_type} {self.name} <{self.account_code}>"

    def balance_movement(
        self, session, start_date: datetime, end_date: datetime
    ) -> Decimal:
        """
        Get the change in the account balance between the given dates.

        Args:
            session (Session): The accounting session to which the Account belongs.
            start_date (datetime): The earliest transaction date for Transaction amounts to be
                included in the balance.
            end_date (datetime): The latest transaction date for Transaction amounts to be included
                in the balance.

        Returns:
            Decimal: The difference between the balance of the Account at the start date and
            end date.
        """
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Balance,
            Ledger,
        )

        start_date, end_date, _, _ = get_dates(session, start_date, end_date)

        query = (
            session.query(
                func.sum(Ledger.amount).label("amount")  # pylint: disable=not-callable
            )
            .filter(Ledger.currency_id == self.currency_id)
            .filter(Ledger.transaction_date >= start_date)
            .filter(Ledger.transaction_date <= end_date)
            .filter(Ledger.post_account_id == self.id)
            .filter(Ledger.entity_id == self.entity_id)
        )
        return (
            query.filter(Ledger.entry_type == Balance.BalanceType.DEBIT).scalar() or 0
        ) - (
            query.filter(Ledger.entry_type == Balance.BalanceType.CREDIT).scalar() or 0
        )

    @staticmethod
    def section_balances(
        session,
        account_types: list,
        start_date: datetime = None,
        end_date: datetime = None,
        full_balance: bool = True,
    ) -> dict:
        """
        Gets the opening, movement and closing balances of the accounts of the given section
        (account types), organized by category.

        Args:
            session (Session): The accounting session to which the Account belongs.
            account_types (`list` of `Account.AccountType`): The Account types
                belonging to the section.
            start_date (datetime): The earliest transaction date for Transaction amounts to be
                included in the balance.
            end_date (datetime): The latest transaction date for Transaction amounts to be included
                in the balance.
            full_balance (bool): Whether to include opening balance amounts in the balance.

        Returns:
            dict: A summary of the total opening, balance movement and closing balance, which
            details of totals by Category and the Accounts contained in each Category.
                - opening (Decimal): The sum of opening balances of Accounts in the section.
                - movement (Decimal): The movememt of the balances of Accounts in the section.
                - closing (Decimal): The sum of opening closing of Accounts in the section.
                - categories (dict): The Accounts belonging to the section separated by Category.
        """
        balances = {"opening": 0, "movement": 0, "closing": 0, "categories": {}}
        start_date, end_date, period_start, _ = get_dates(session, start_date, end_date)

        for account in session.scalars(
            select(Account).filter(Account.account_type.in_(account_types))
        ).all():
            account.opening = account.opening_balance(
                session, end_date.year
            ) + account.balance_movement(session, period_start, start_date)
            movement = account.balance_movement(session, start_date, end_date)
            account.closing = account.opening + movement if full_balance else movement
            account.movement = movement * -1  # cashflow statement display
            if account.closing != 0 or account.movement != 0:
                category_id, category_name = (
                    (0, Account.AccountType[account.account_type.name].value)
                    if account.category is None
                    else (account.category_id, account.category.name)
                )
                if (
                    category_name
                    in balances[  # pylint: disable=consider-iterating-dictionary
                        "categories"  # pylint: disable=consider-iterating-dictionary
                    ].keys()  # pylint: disable=consider-iterating-dictionary
                ):
                    balances["categories"][category_name]["total"] += account.closing
                    balances["categories"][category_name]["accounts"].append(account)
                else:
                    balances["categories"].update(
                        {
                            category_name: {
                                "id": category_id,
                                "total": account.closing,
                                "accounts": [account],
                            }
                        }
                    )
                balances["opening"] += account.opening
                balances["movement"] += account.movement
                balances["closing"] += account.closing
        return balances

    def opening_balance(self, session, year: int = None) -> Decimal:
        """
        Gets the the opening balance for the account for the given year.

        Args:
            session (Session): The accounting session to which the Account belongs.
            year (int): The calendar year for which to retrieve the opening balance.

        Returns:
            Decimal: The total opening balance of the Account for the year.

        """
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Balance,
        )

        period_id = (
            ReportingPeriod.get_period(
                session, datetime(year, session.entity.year_start, 1, 0, 0, 0)
            ).id
            if year
            else session.entity.reporting_period_id
        )
        query = (
            session.query(
                func.sum(Balance.amount).label("amount")  # pylint: disable=not-callable
            )
            .filter(Balance.currency_id == self.currency_id)
            .filter(Balance.reporting_period_id == period_id)
            .filter(Balance.account_id == self.id)
            .filter(Balance.entity_id == self.entity_id)
        )
        return (
            query.filter(Balance.balance_type == Balance.BalanceType.DEBIT).scalar()
            or 0
        ) - (
            query.filter(Balance.balance_type == Balance.BalanceType.CREDIT).scalar()
            or 0
        )

    def closing_balance(self, session, end_date: datetime = None) -> Decimal:
        """
        Gets the the closing balance of the Account as at the given date.

        Args:
            session (Session): The accounting session to which the Account belongs.
            end_date (datetime): The latest transaction date for Transaction
                amounts to be included in the balance.

        Returns:
            Decimal: The total opening balance of the Account for the year.

        """

        start_date, end_date, _, _ = get_dates(session, None, end_date)

        return self.opening_balance(session, end_date.year) + self.balance_movement(
            session, start_date, end_date
        )

    def statement(  # pylint: disable=too-many-locals
        self,
        session,
        start_date: datetime = None,
        end_date: datetime = None,
        schedule: bool = False,
    ) -> dict:
        # pylint: disable=line-too-long
        """
        Gets a chronological listing of the Transactions posted to the Account between
            the dates given.

        Args:
            session (Session): The accounting session to which the Account belongs.
            start_date (datetime): The earliest transaction date for Transaction amounts
                to be included in the statement.
            end_date (datetime): The latest transaction date for Transaction amounts to
                be included in the statement.
            schedule (bool): Whether to exclude assignable Transactions and only list
                clearable Transactions with outstanding amounts.

        Raises:
            InvalidAccountTypeError: If the Account type is not Receivable or Payable.

        Returns:
            dict: With a A summary of the opening and closing balance in the case of
            a statement, the total, cleared and uncleared amounts if its a schedule
            together with a list of Transactions.

            Statements.
                - opening_balance (Decimal): The balance of the Account at the beginning of the statement period.
                - transactions (list): Transactions posted to the Account during the period.
                - closing_balance (Decimal): The balance of the Account at the end of the statement period.
            Schedule.
                - transactions (list): Outstanding clearable Transactions posted to the Account as at the end date.
                - total_amount (Decimal): The total amount of the Transactions in the Schdeule.
                - cleared_amount (Decimal): The amount of the Transactions in the Schdeule that has been cleared.
                - uncleared_amount (Decimal): The amount of the Transactions in the Schdeule that is still outstanding.
        """
        # pylint: enable=line-too-long
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Transaction,
            Ledger,
            Assignment,
            Balance,
        )

        if schedule and self.account_type not in [
            Account.AccountType.RECEIVABLE,
            Account.AccountType.PAYABLE,
        ]:
            raise InvalidAccountTypeError(
                "Only Receivable and Payable Accounts can have a statement/schedule."
            )
        start_date, end_date, _, period_id = get_dates(session, start_date, end_date)

        statement = (
            {
                "transactions": [],
                "total_amount": 0,
                "cleared_amount": 0,
                "uncleared_amount": 0,
            }
            if schedule
            else {
                "opening_balance": self.opening_balance(session, end_date.year),
                "transactions": [],
                "closing_balance": 0,
            }
        )
        balances = []

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", "SELECT statement has a cartesian product.*", exc.SAWarning
            )
            ledger = aliased(Ledger, flat=True)
            transactions = (
                session.query(Transaction)
                .join(ledger, ledger.transaction_id == Transaction.id)
                .filter(Transaction.currency_id == self.currency_id)
                .filter(Transaction.transaction_date <= end_date)
                .filter(
                    or_(
                        ledger.post_account_id == self.id,
                        ledger.folio_account_id == self.id,
                    )
                )
                .filter(Transaction.entity_id == self.entity_id)
                .filter(Ledger.entity_id == self.entity_id)
            )
            if schedule:
                transactions = transactions.filter(
                    Transaction.transaction_type.in_(Assignment.clearables)
                )

                balances = (
                    session.query(Balance)
                    .filter(Balance.account_id == self.id)
                    .filter(Balance.reporting_period_id == period_id)
                    .filter(Balance.entity_id == self.entity_id)
                    .order_by(Balance.transaction_date)
                )
            else:
                transactions = transactions.filter(
                    Transaction.transaction_date >= start_date
                )
                balance = statement["opening_balance"]

            for transaction in list(balances) + list(
                transactions.order_by(Transaction.transaction_date).distinct()
            ):
                if schedule:
                    cleared = transaction.cleared(session)
                    if (
                        transaction.amount  # pylint: disable=too-many-boolean-expressions
                        - cleared
                        == 0
                        or (
                            transaction.transaction_type
                            == Transaction.TransactionType.JOURNAL_ENTRY
                            and (
                                (
                                    self.account_type == Account.AccountType.RECEIVABLE
                                    and transaction.credited
                                )
                                or (
                                    self.account_type == Account.AccountType.PAYABLE
                                    and not transaction.credited
                                )
                            )
                        )
                    ):
                        continue
                    (
                        transaction.cleared_amount,
                        transaction.uncleared_amount,
                        transaction.age,
                    ) = (
                        cleared,
                        transaction.amount - cleared,
                        (end_date - transaction.transaction_date).days,
                    )
                    statement["total_amount"] += transaction.amount
                    statement["cleared_amount"] += transaction.cleared_amount
                    statement["uncleared_amount"] += transaction.uncleared_amount
                else:
                    contribution = transaction.contribution(session, self)
                    balance += contribution
                    transaction.balance = balance

                    transaction.debit, transaction.credit = (
                        (0, abs(contribution))
                        if contribution < 0
                        else (contribution, 0)
                    )
                    statement["closing_balance"] = balance

                statement["transactions"].append(transaction)

        return statement

    def validate(self, session) -> None:
        """
        Validates the Account properties.

        Args:
            session (Session): The accounting session to which the Account belongs.

        Raises:
            InvalidCategoryAccountTypeError: If the account type of the Account
                does not match that of its assigned Category.

        Returns:
            None
        """
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Category,
        )

        self.name = self.name.title()
        if (
            self.account_code is None
            or len(inspect(self).attrs.account_type.history.deleted) > 0
        ):
            self.account_code = self._get_account_code(session)

        if self.category_id:
            category = session.get(Category, self.category_id)
            if self.account_type != category.category_account_type:
                raise InvalidCategoryAccountTypeError(
                    self.account_type.value, category.category_account_type.value
                )

    def validate_delete(self, session) -> None:
        """
        Validates if the account can be deleted.

        Args:
            session (Session): The accounting session to which the Account belongs.

        Raises:
            HangingTransactionsError: If the Account has had Transactions during the
                current Reporting period.

        Returns:
            None
        """
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Ledger,
        )

        if (
            session.query(func.count(Ledger.id))  # pylint: disable=not-callable
            .filter(Ledger.entity_id == self.entity_id)
            .filter(
                or_(
                    Ledger.post_account_id == self.id,
                    Ledger.folio_account_id == self.id,
                )
            )
            .scalar()
            > 0
        ):
            raise HangingTransactionsError("Account")
