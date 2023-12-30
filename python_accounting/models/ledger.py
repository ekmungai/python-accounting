import hashlib
from datetime import datetime
from copy import deepcopy
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Enum, func
from typing import Any
from sqlalchemy.types import DECIMAL
from strenum import StrEnum
from python_accounting.mixins import IsolatingMixin
from python_accounting.config import config
from .recyclable import Recyclable
from .balance import Balance
from .transaction import Transaction


class Ledger(IsolatingMixin, Recyclable):
    """Represents a record in the Ledger. This class should never have to be invoked directly"""

    __mapper_args__ = {"polymorphic_identity": "Ledger"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    transaction_date: Mapped[datetime] = mapped_column()
    entry_type: Mapped[StrEnum] = mapped_column(Enum(Balance.BalanceType))
    amount: Mapped[Decimal] = mapped_column(DECIMAL(precision=13, scale=4))
    hash: Mapped[str] = mapped_column(String(500), nullable=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transaction.id", ondelete="RESTRICT")
    )
    currency_id: Mapped[int] = mapped_column(
        ForeignKey("currency.id", ondelete="RESTRICT")
    )
    post_account_id: Mapped[int] = mapped_column(
        ForeignKey("account.id", ondelete="RESTRICT")
    )
    folio_account_id: Mapped[int] = mapped_column(
        ForeignKey("account.id", ondelete="RESTRICT")
    )
    line_item_id: Mapped[int] = mapped_column(
        ForeignKey("line_item.id", ondelete="RESTRICT")
    )
    tax_id: Mapped[int] = mapped_column(
        ForeignKey("tax.id", ondelete="RESTRICT"), nullable=True
    )

    # relationships
    transaction: Mapped["Transaction"] = relationship(foreign_keys=[transaction_id])
    currency: Mapped["Currency"] = relationship(foreign_keys=[currency_id])
    post_account: Mapped["Account"] = relationship(foreign_keys=[post_account_id])
    folio_account: Mapped["Account"] = relationship(foreign_keys=[folio_account_id])
    line_item: Mapped["LineItem"] = relationship(foreign_keys=[line_item_id])

    @staticmethod
    def _transaction_ledgers(transaction: Transaction) -> tuple:
        """Prepare the ledgers for the transaction"""
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
    def _post_compound(session, transaction: Transaction) -> None:  # TODO
        """Post a compound transaction to the ledger"""
        pass

    @staticmethod
    def _post_simple(session, transaction: Transaction) -> None:
        """Post a simple transaction to the ledger"""

        for line_item in transaction.line_items:
            amount = line_item.amount * line_item.quantity
            post, folio = Ledger._transaction_ledgers(transaction)
            post.transaction_id = folio.transaction_id = transaction.id
            post.currency_id = folio.currency_id = transaction.currency_id
            post.transaction_date = (
                folio.transaction_date
            ) = transaction.transaction_date
            post.line_item_id = folio.line_item_id = line_item.id

            if line_item.tax_id:
                tax_post, tax_folio = deepcopy(post), deepcopy(folio)
                tax_post.amount = tax_folio.amount = amount * line_item.tax.rate / 100
                tax_post.post_account_id = tax_folio.folio_account_id = (
                    line_item.account_id
                    if line_item.tax_inclusive
                    else transaction.account_id
                )
                tax_post.folio_account_id = (
                    tax_folio.post_account_id
                ) = line_item.tax.account_id

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
        """Post the Transaction to the ledger"""
        if transaction.compound:
            Ledger._post_compound(session, transaction)
        else:
            Ledger._post_simple(session, transaction)

    def get_hash(self, session) -> str:
        """Calculate the hash of the ledger"""

        last = session.query(Ledger).order_by(Ledger.id.desc()).first()
        self.previous_hash = last.hash if last else config.hashing["salt"]

        return getattr(hashlib, config.hashing["algorithm"])(
            ",".join(
                list(
                    map(
                        str,
                        [
                            self.transaction_date,
                            self.entry_type,
                            self.amount,
                            self.previous_hash,
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

    def validate(self, session) -> None:
        """Validate the ledger properties"""

        self.hash = self.get_hash(session)
