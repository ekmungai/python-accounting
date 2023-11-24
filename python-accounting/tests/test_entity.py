from sqlalchemy.orm import Session
from sqlalchemy import select
from database.engine import engine
from models.entity import Entity
from models.currency import Currency


def test_entity_reporting_currency():
    """Tests the relationship between an entity and its reporting currency"""

    with Session(engine) as session:
        currency = Currency(name="US Dollars", code="USD")
        session.add(currency)
        session.flush()
        entity = Entity(name="Test Entity", currency_id=currency.id)
        session.add(entity)
        session.commit()
        entity = session.scalar(select(Entity).where(Entity.id == entity.id))
        assert entity.name == "Test Entity"
        assert entity.currency.name == "US Dollars"
        assert entity.currency.code == "USD"
