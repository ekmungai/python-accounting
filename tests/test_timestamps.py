"""Record timestamps are taken when the record is saved, not when the library is imported."""

import time

from python_accounting.models import Currency


def test_created_at_is_the_time_of_saving(session, entity):
    """Records saved at different times have different creation times."""
    first = Currency(name="Kenya Shillings", code="KES", entity_id=entity.id)
    session.add(first)
    session.commit()
    time.sleep(0.05)
    second = Currency(name="Euro", code="EUR", entity_id=entity.id)
    session.add(second)
    session.commit()

    assert second.created_at > first.created_at


def test_updated_at_changes_on_update(session, entity):
    """Updating a record moves its modification time on."""
    currency = Currency(name="Pound", code="GBP", entity_id=entity.id)
    session.add(currency)
    session.commit()
    created = currency.updated_at
    time.sleep(0.05)
    currency.name = "Pound Sterling"
    session.commit()

    assert currency.updated_at > created
