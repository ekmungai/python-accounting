from sqlalchemy import select
from python_accounting.models import Currency, Entity


def test_currency_entity(session, entity):
    """Tests the relationship between a currency and its associated entity"""

    currency = Currency(name="US Dollars", code="USD", entity_id=entity.id)
    session.add(currency)
    session.commit()

    currency = session.get(Currency, currency.id)
    assert currency.entity.name == "Test Entity"


def test_currency_isolation(session, entity):
    """Tests the isolation of currency objects by entity"""

    entity2 = Entity(name="Test Entity Two")
    session.add(entity2)
    session.flush()
    entity2 = session.get(Entity, entity2.id)

    session.add_all(
        [
            Currency(name="US Dollars", code="USD", entity_id=entity.id),
            Currency(name="Euro", code="EUR", entity_id=entity2.id),
        ]
    )
    session.commit()

    currencies = session.scalars(select(Currency)).all()

    assert len(currencies) == 1
    assert currencies[0].name == "US Dollars"
    assert currencies[0].code == "USD"
    assert currencies[0].entity.name == "Test Entity"

    currency2 = session.get(Currency, 2)
    assert currency2 == None

    session.entity = entity2
    currencies = session.scalars(select(Currency)).all()

    assert len(currencies) == 1
    assert currencies[0].name == "Euro"
    assert currencies[0].code == "EUR"
    assert currencies[0].entity.name == "Test Entity Two"

    currency1 = session.get(Currency, 1)
    assert currency1 == None


def test_currency_recycling(session, entity):
    """Tests the deleting, restoring and destroying functions of the currency model"""

    currency = Currency(name="US Dollars", code="USD", entity_id=entity.id)
    session.add(currency)
    session.flush()

    currency_id = currency.id

    session.delete(currency)

    currency = session.get(Currency, currency_id)
    assert currency == None

    currency = session.get(Currency, currency_id, include_deleted=True)
    assert currency != None
    session.restore(currency)

    currency = session.get(Currency, currency_id)
    assert currency != None

    session.destroy(currency)

    currency = session.get(Currency, currency_id)
    assert currency == None

    currency = session.get(Currency, currency_id, include_deleted=True)
    assert currency != None
    session.restore(currency)  # destroyed models canot be restored

    currency = session.get(Currency, currency_id)
    assert currency == None
