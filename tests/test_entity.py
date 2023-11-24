import pytest
import python_accounting.models as models
from sqlalchemy.orm import Session
from sqlalchemy import select, create_engine


@pytest.fixture
def engine():
    engine = create_engine(f"sqlite://", echo=True)
    models.Base.metadata.create_all(engine)
    return engine


def test_entity_reporting_currency(engine):
    """Tests the relationship between an entity and its reporting currency"""

    with Session(engine) as session:
        currency = models.Currency(name="US Dollars", code="USD")
        session.add(currency)
        session.flush()
        entity = models.Entity(name="Test Entity", currency_id=currency.id)
        session.add(entity)
        session.commit()
        entity = session.scalar(
            select(models.Entity).where(models.Entity.id == entity.id)
        )
        assert entity.name == "Test Entity"
        assert entity.currency.name == "US Dollars"
        assert entity.currency.code == "USD"
