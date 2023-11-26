import pytest
from sqlalchemy import select, create_engine
import python_accounting.models as models
from python_accounting.database.session import Session
from python_accounting.exceptions import MissingEntityError


@pytest.fixture
def engine():
    engine = create_engine(f"sqlite://", echo=False)
    models.Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def entity(session):
    entity = models.Entity(name="Test Entity")
    session.add(entity)
    session.commit()
    return session.get(models.Entity, entity.id)


def test_entity_reporting_currency(entity, session):
    """Tests the relationship between an entity and its reporting currency"""

    currency = models.Currency(name="US Dollars", code="USD", entity_id=entity.id)
    session.add(currency)
    session.flush()

    entity.currency_id = currency.id
    session.commit()
    assert entity.name == "Test Entity"
    assert entity.currency.name == "US Dollars"
    assert entity.currency.code == "USD"

    currency = session.get(models.Currency, currency.id)
    assert currency.entity.name == "Test Entity"


def test_entity_isolation(session, entity):
    """Tests the isolation of accounting objects by entity"""

    session.entity = None
    isolated_user = models.User(name="Isolated User", email="isolated@microbooks.io")
    with pytest.raises(MissingEntityError):
        session.add(isolated_user)

    session.expunge(isolated_user)

    entity2 = models.Entity(name="Test Entity Two")
    session.add(entity2)
    session.flush()
    entity2 = session.get(models.Entity, entity2.id)

    session.add_all(
        [
            models.User(
                name="Test User 1", email="one@microbooks.io", entity_id=entity.id
            ),
            models.User(
                name="Test User 2", email="two@microbooks.io", entity_id=entity2.id
            ),
        ]
    )
    session.commit()

    users = list(session.scalars(select(models.User)))

    assert len(users) == 1
    assert users[0].name == "Test User 2"  # From the creation of entity 2 above
    assert users[0].entity.name == "Test Entity Two"

    user1 = session.get(models.User, 1)
    assert user1 == None

    session.entity = entity
    users = list(session.scalars(select(models.User)))

    assert len(users) == 1
    assert users[0].name == "Test User 1"
    assert users[0].entity.name == "Test Entity"

    user1 = session.get(models.User, 2)
    assert user1 == None


def test_entity_users(session, entity):
    """Tests the relationship between an entity and its users"""

    user1 = models.User(
        name="Test User 1", email="one@microbooks.io", entity_id=entity.id
    )
    user2 = models.User(
        name="Test User 2", email="two@microbooks.io", entity_id=entity.id
    )
    session.add_all([user1, user2])

    session.commit()
    entity = session.get(models.Entity, entity.id)
    assert entity.users[0].name == "Test User 1"
    assert entity.users[1].name == "Test User 2"


def test_entity_recycling(session, entity):
    """Tests the deleting, restoring and destroying functions of the entity model"""

    session.delete(entity)
    session.flush()
