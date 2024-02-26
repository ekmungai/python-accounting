import pytest
from datetime import datetime
from sqlalchemy import select
from python_accounting.models import Entity, Currency, User
from python_accounting.exceptions import MissingEntityError, SessionEntityError


def test_entity_reporting_currency(session, entity):
    """Tests the relationship between an entity and its reporting currency"""

    currency = Currency(name="US Dollars", code="USD", entity_id=entity.id)
    session.add(currency)
    session.flush()

    entity.currency_id = currency.id
    session.commit()
    assert entity.name == "Test Entity"
    assert entity.currency.name == "US Dollars"
    assert entity.currency.code == "USD"


def test_entity_reporting_period_and_users(session, entity):
    """Tests the relationship between an entity, its current reporting period and users"""
    year = datetime.today().year
    assert entity.reporting_period.calendar_year == year
    assert entity.reporting_period.period_count == 1

    entity.reporting_period.calendar_year = year - 1
    session.flush()

    assert entity.reporting_period.calendar_year == year - 1

    user = User(name="Test User 1", email="one@microbooks.io", entity_id=entity.id)
    session.add(user)
    session.flush()
    entity = session.get(Entity, entity.id)
    assert entity.reporting_period.period_count == 2
    assert entity.users[0] == user


def test_entity_isolation(session, entity):
    """Tests the isolation of accounting objects by entity"""

    session.entity = None
    isolated_user = User(name="Isolated User", email="isolated@microbooks.io")
    with pytest.raises(MissingEntityError):
        session.add(isolated_user)

    session.expunge(isolated_user)

    entity2 = Entity(name="Test Entity Two")
    session.add(entity2)
    session.flush()
    entity2 = session.get(Entity, entity2.id)

    session.add_all(
        [
            User(name="Test User 1", email="one@microbooks.io", entity_id=entity.id),
            User(name="Test User 2", email="two@microbooks.io", entity_id=entity2.id),
        ]
    )
    session.commit()

    users = session.scalars(select(User)).all()

    assert len(users) == 1
    assert (
        users[0].name == "Test User 2"
    )  # From the creation of entity 2 above, when session.entity was None
    assert users[0].entity.name == "Test Entity Two"

    user1 = session.get(User, 1)
    assert user1 == None

    session.entity = entity
    users = session.scalars(select(User)).all()

    assert len(users) == 1
    assert users[0].name == "Test User 1"
    assert users[0].entity.name == "Test Entity"

    user2 = session.get(User, 2)
    assert user2 == None


def test_entity_users(session, entity):
    """Tests the relationship between an entity and its users"""

    user1 = User(name="Test User 1", email="one@microbooks.io", entity_id=entity.id)
    user2 = User(name="Test User 2", email="two@microbooks.io", entity_id=entity.id)
    session.add_all([user1, user2])

    session.commit()
    entity = session.get(Entity, entity.id)
    assert entity.users[0].name == "Test User 1"
    assert entity.users[1].name == "Test User 2"


def test_entity_recycling(session, entity):
    """Tests the deleting, restoring and destroying functions of the entity model"""

    with pytest.raises(SessionEntityError):
        session.delete(entity)

    entity2 = Entity(name="Test Entity Two")
    session.add(entity2)
    session.flush()

    entity_id = entity2.id

    session.delete(entity2)

    entity2 = session.get(Entity, entity_id)
    assert entity2 == None

    entity2 = session.get(Entity, entity_id, include_deleted=True)
    assert entity2 != None
    session.restore(entity2)

    entity2 = session.get(Entity, entity_id)
    assert entity2 != None

    session.destroy(entity2)

    entity2 = session.get(Entity, entity_id)
    assert entity2 == None

    entity2 = session.get(Entity, entity_id, include_deleted=True)
    assert entity2 != None
    session.restore(entity2)  # destroyed models canot be restored

    entity2 = session.get(Entity, entity_id)
    assert entity2 == None
