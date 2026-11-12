"""Sessions that are not accounting sessions are not affected by the accounting listeners."""

from sqlalchemy import String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from python_accounting.models import Account


class OtherBase(DeclarativeBase):  # pylint: disable=too-few-public-methods
    """A model base unrelated to the accounting models."""


class Note(OtherBase):  # pylint: disable=too-few-public-methods
    """A model of another part of the application."""

    __tablename__ = "other_note"
    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(String(50))


def test_plain_session_beside_accounting_session(engine, session, entity, currency):
    """A plain Session can add and query its own models while an accounting session is in use."""
    OtherBase.metadata.create_all(engine)

    with Session(engine) as plain:
        plain.add(Note(text="not accounting"))
        plain.commit()
        assert plain.scalars(select(Note)).one().text == "not accounting"

    account = Account(
        name="Bank",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(account)
    session.commit()
    assert session.get(Account, account.id).name == "Bank"
