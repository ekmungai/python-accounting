from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from python_accounting.models import Entity, Base, Currency, LineItem
from python_accounting.database.session import get_session
from python_accounting.config import config


@pytest.fixture
def engine():
    database = config.database
    engine = create_engine(database["url"], echo=database["echo"])
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    with get_session(engine) as session:
        yield session


@pytest.fixture
def entity(session):
    entity = Entity(name="Test Entity")
    session.add(entity)
    session.commit()
    return session.get(Entity, entity.id)


@pytest.fixture
def currency(session, entity):
    currency = Currency(name="US Dollars", code="USD", entity_id=entity.id)
    session.add(currency)
    session.commit()
    return session.get(Currency, currency.id)


@pytest.fixture
def post_document(session):
    """Returns a function that posts a single line document to the given account."""

    def post(document_type, account, line_account, date, amount):
        document = document_type(
            narration="Test document",
            transaction_date=date,
            account_id=account.id,
            entity_id=account.entity_id,
        )
        session.add(document)
        session.flush()
        line = LineItem(
            narration="Test line",
            account_id=line_account.id,
            amount=Decimal(amount),
            entity_id=account.entity_id,
        )
        session.add(line)
        session.flush()
        document.line_items.add(line)
        session.flush()
        document.post(session)
        return document

    return post


@pytest.fixture
def fixed_today(monkeypatch):
    """Freezes today to midday on 31 January of the current year for reports and bulk assignment."""
    year = datetime.now().year

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(year, 1, 31, 12, tzinfo=tz)

        @classmethod
        def today(cls):
            return cls.now()

    monkeypatch.setattr("python_accounting.utils.dates.datetime", FixedDateTime)
    monkeypatch.setattr("python_accounting.mixins.assigning.datetime", FixedDateTime)
    return FixedDateTime.today()
