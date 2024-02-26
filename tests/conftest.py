import pytest
from sqlalchemy import create_engine
from python_accounting.models import Entity, Base, Currency
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
