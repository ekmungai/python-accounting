# models/ledger.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents an entry in the Ledger.

"""
import hashlib
from datetime import datetime
from copy import deepcopy
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum, select
from sqlalchemy.types import DECIMAL
from strenum import StrEnum
from python_accounting.mixins import IsolatingMixin
from python_accounting.config import config
from python_accounting.models import Recyclable, Balance, Transaction


class Ledger(  # pylint: disable=too-many-instance-attributes
    IsolatingMixin, Recyclable
):
    """Represents an entry in the Ledger. (Should never have to be invoked directly)."""

    __mapper_args__ = {"polymorphic_identity": "Ledger"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    """(int): The primary key of the ledger database record."""
    transaction_date: Mapped[datetime] = mapped_column()
    """(datetime): The date of the Transaction associated with the Ledger."""
    entry_type: Mapped[StrEnum] = mapped_column(Enum(Balance.BalanceType))
    """(BalanceType): The side of the double entry to which the Ledger is posted."""
    amount: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4))
    """(Decimal): The amount posted to the Ledger by the entry."""
    hash: Mapped[str] = mapped_column(String(500), nullable=True)
    """(str): The encoded contents of the Ledger entry."""
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transaction.id", ondelete="RESTRICT")
    )
    """(int): The id of the Transaction associated with the Ledger."""
    currency_id: Mapped[int] = mapped_column(
        ForeignKey("currency.id", ondelete="RESTRICT")
    )
    """(int): The id of the Currency associated with the Ledger."""
    post_account_id: Mapped[int] = mapped_column(
        ForeignKey("account.id", ondelete="RESTRICT")
    )
    """(int): The id of the Account to which the Ledger is posted."""
    folio_account_id: Mapped[int] = mapped_column(
        ForeignKey("account.id", ondelete="RESTRICT")
    )
    """(int): The id of the Account to which the opposite side of Ledger is posted."""
    line_item_id: Mapped[int] = mapped_column(
        ForeignKey("line_item.id", ondelete="RESTRICT"), nullable=True
    )
    """(`int`, optional): The id of the Line Item associated with the Ledger."""
    tax_id: Mapped[int] = mapped_column(
        ForeignKey("tax.id", ondelete="RESTRICT"), nullable=True
    )
    """(`int`, optional): The id of the Tax associated with the Ledger."""

    # relationships
    transaction: Mapped["Transaction"] = relationship(foreign_keys=[transaction_id])
    """(Transaction): The Transaction associated with the Ledger."""
    currency: Mapped["Currency"] = relationship(foreign_keys=[currency_id])
    """(Currency): The Currency associated with the Ledger."""
    post_account: Mapped["Account"] = relationship(foreign_keys=[post_account_id])
    """(Account): The main Account associated with the Ledger."""
    folio_account: Mapped["Account"] = relationship(foreign_keys=[folio_account_id])
    """(Account): The oppeite double entry Account associated with the Ledger."""
    line_item: Mapped["LineItem"] = relationship(foreign_keys=[line_item_id])
    """(LineItem): The LineItem associated with the Ledger."""

    def __repr__(self) -> str:
        return f"""Post {self.post_account.name},
         Folio {self.folio_account.name}
         <{self.entry_type}> :
         {self.amount}"""

    @staticmethod
    def _allocate_amount(  # pylint: disable=too-many-arguments
        session, post, amount, posts, folios, transaction, entry_type
    ) -> None:
        if amount == 0:
            posts.pop(0)
            return Ledger._make_compound_ledgers(
                session, posts, folios, transaction, entry_type
            )
        folio, folio_amount = folios[0]
        ledger = Ledger(
            transaction_id=transaction.id,
            currency_id=transaction.currency_id,
            transaction_date=transaction.transaction_date,
            entity_id=transaction.entity_id,
            entry_type=entry_type,
            post_account_id=post,
            folio_account_id=folio,
        )

        if folio_amount > amount:
            ledger.amount = amount
            folios[0][1] -= amount
            amount = 0
        else:
            ledger.amount = folio_amount
            amount -= folio_amount
            folios.pop(0)

        session.add(ledger)
        session.commit()

        return Ledger._allocate_amount(
            session, post, amount, posts, folios, transaction, entry_type
        )

    @staticmethod
    def _make_compound_ledgers(
        session,
        posts: list,
        folios: list,
        transaction: Transaction,
        entry_type: Balance.BalanceType,
    ) -> None:
        if posts == []:
            return None
        post, post_amount = posts[0]
        return Ledger._allocate_amount(
            session, post, post_amount, posts, folios, transaction, entry_type
        )

    @staticmethod
    def _post_compound(session, transaction: Transaction) -> None:
        # Debit amounts ledgers
        debit_ledgers, credit_ledgers = transaction.get_compound_entries()
        Ledger._make_compound_ledgers(
            session,
            debit_ledgers,
            credit_ledgers,
            transaction,
            Balance.BalanceType.DEBIT,
        )

        # Credit amounts ledgers
        debit_ledgers, credit_ledgers = transaction.get_compound_entries()
        Ledger._make_compound_ledgers(
            session,
            credit_ledgers,
            debit_ledgers,
            transaction,
            Balance.BalanceType.CREDIT,
        )

    @staticmethod
    def _transaction_ledgers(transaction: Transaction) -> tuple:
        post, folio = Ledger(), Ledger()
        post.entity_id = folio.entity_id = transaction.entity_id
        post.entry_type, folio.entry_type = (
            (
                Balance.BalanceType.CREDIT,
                Balance.BalanceType.DEBIT,
            )
            if transaction.credited
            else (
                Balance.BalanceType.DEBIT,
                Balance.BalanceType.CREDIT,
            )
        )
        return post, folio

    @staticmethod
    def _post_simple(session, transaction: Transaction) -> None:
        for line_item in transaction.line_items:
            amount = line_item.amount * line_item.quantity
            post, folio = Ledger._transaction_ledgers(transaction)
            post.transaction_id = folio.transaction_id = transaction.id
            post.currency_id = folio.currency_id = transaction.currency_id
            post.transaction_date = folio.transaction_date = (
                transaction.transaction_date
            )
            post.line_item_id = folio.line_item_id = line_item.id

            if line_item.tax_id:
                tax_post, tax_folio = deepcopy(post), deepcopy(folio)
                tax_post.amount = tax_folio.amount = (
                    amount - (amount / (1 + line_item.tax.rate / 100))
                    if line_item.tax_inclusive
                    else amount * line_item.tax.rate / 100
                )
                tax_post.post_account_id = tax_folio.folio_account_id = (
                    line_item.account_id
                    if line_item.tax_inclusive
                    else transaction.account_id
                )
                tax_post.folio_account_id = tax_folio.post_account_id = (
                    line_item.tax.account_id
                )

                session.add(tax_post)
                session.flush()

                session.add(tax_folio)
                session.flush()

            post.tax_id = folio.tax_id = line_item.tax_id
            post.amount = folio.amount = amount

            post.post_account_id = folio.folio_account_id = transaction.account_id
            post.folio_account_id = folio.post_account_id = line_item.account_id

            session.add(post)
            session.flush()

            session.add(folio)
            session.commit()

    @staticmethod
    def post(session, transaction: Transaction) -> None:
        """
        Posts the Transaction to the ledger.

        Args:
            session (Session): The accounting session to which the Account belongs.
            transaction (Transaction): The Transaction to be posted.
        """
        if transaction.compound:
            Ledger._post_compound(session, transaction)
        else:
            Ledger._post_simple(session, transaction)

    def get_hash(self, connection) -> None:
        """
        Calculate the hash of the Ledger.

        Args:
            connection (Connection): The database connection of the accounting session
            to which the Ledger belongs.

        Returns:
            None
        """
        last = connection.execute(
            select(Ledger).where(Ledger.id == self.id - 1)
        ).fetchone()

        return getattr(hashlib, config.hashing["algorithm"])(
            ",".join(
                list(
                    map(
                        str,
                        [
                            self.transaction_date.replace(microsecond=0),
                            self.entry_type,
                            round(Decimal(self.amount), 4).normalize(),
                            last.hash if last else config.hashing["salt"],
                            self.entity_id,
                            self.transaction_id,
                            self.currency_id,
                            self.post_account_id,
                            self.folio_account_id,
                            self.line_item_id,
                            self.tax_id,
                        ],
                    )
                )
            ).encode()
        ).hexdigest()
