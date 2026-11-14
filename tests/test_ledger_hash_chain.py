"""The ledger hash chain links each Ledger record to the previous Ledger record of its Entity."""

from datetime import datetime

import pytest
from sqlalchemy import update

from python_accounting.config import config
from python_accounting.models import Account, Ledger
from python_accounting.transactions import JournalEntry


@pytest.fixture
def accounts(session, entity, currency):
    """A bank and a revenue account."""
    bank = Account(
        name="Bank",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    revenue = Account(
        name="Revenue",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([bank, revenue])
    session.commit()
    return bank, revenue


def _tamper_hash(session, ledger_id):
    session.connection().execute(
        update(Ledger).where(Ledger.id == ledger_id).values(hash="tampered")
    )
    session.expire_all()


def test_entity_chain_detects_a_changed_predecessor(
    monkeypatch, session, accounts, post_document
):
    """With the entity chain, changing a Ledger hash breaks the next Transaction's Ledgers."""
    monkeypatch.setitem(config.hashing, "chain", "entity")
    bank, revenue = accounts
    first = post_document(JournalEntry, bank, revenue, datetime.now(), "100")
    second = post_document(JournalEntry, bank, revenue, datetime.now(), "50")
    session.commit()
    assert first.is_secure(session)
    assert second.is_secure(session)

    _tamper_hash(session, max(ledger.id for ledger in first.ledgers))

    assert not first.is_secure(session)
    assert not second.is_secure(session)


def test_entity_chain_starts_from_the_salt(monkeypatch, session, accounts, post_document):
    """The first Ledger record of an Entity is hashed with the salt."""
    monkeypatch.setitem(config.hashing, "chain", "entity")
    bank, revenue = accounts
    first = post_document(JournalEntry, bank, revenue, datetime.now(), "100")
    session.commit()
    assert first.is_secure(session)


def test_configure_hashing_chain():
    """The chain defaults to legacy and accepts only the known values."""
    original = dict(config.hashing)
    try:
        config.configure_hashing()
        assert config.hashing["chain"] == "legacy"
        config.configure_hashing(chain="entity")
        assert config.hashing["chain"] == "entity"
        with pytest.raises(ValueError):
            config.configure_hashing(chain="other")
    finally:
        config.hashing.clear()
        config.hashing.update(original)
