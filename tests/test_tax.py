import pytest
from sqlalchemy import select
from python_accounting.models import (
    Tax,
    Entity,
    Account,
)
from python_accounting.exceptions import (
    InvalidTaxAccountError,
    NegativeAmountError,
    MissingTaxAccountError,
)


def test_tax_entity(session, entity, currency):
    """Tests the relationship between a tax and its associated entity"""

    account = Account(
        name="test tax account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)
    session.flush()

    tax = Tax(
        name="Output Vat",
        code="OTPT",
        account_id=account.id,
        rate=10,
        entity_id=entity.id,
    )
    session.add(tax)
    session.commit()

    tax = session.get(Tax, tax.id)
    assert tax.entity.name == "Test Entity"
    assert tax.account.name == "Test Tax Account"


def test_tax_validation(session, entity, currency):
    """Tests the validation of tax objects"""

    account = Account(
        name="test tax account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)
    session.flush()

    tax = Tax(
        name="Output Vat",
        code="OTPT",
        account_id=account.id,
        rate=-1,
        entity_id=entity.id,
    )
    session.add(tax)
    with pytest.raises(NegativeAmountError):
        session.commit()

    tax.rate = 10
    session.add(tax)

    account.account_type = Account.AccountType.OPERATING_REVENUE
    session.add(account)

    with pytest.raises(InvalidTaxAccountError):
        session.commit()

    account.account_type = Account.AccountType.CONTROL
    session.add(account)
    session.flush()

    tax.account_id = None
    session.add(tax)
    with pytest.raises(MissingTaxAccountError):
        session.commit()


def test_tax_isolation(session, entity, currency):
    """Tests the isolation of tax objects by entity"""

    account = Account(
        name="test tax account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)
    session.flush()

    entity2 = Entity(name="Test Entity Two")
    session.add(entity2)
    session.flush()
    entity2 = session.get(Entity, entity2.id)

    session.add_all(
        [
            Tax(
                name="Output Vat",
                code="OTPT",
                account_id=account.id,
                rate=10,
                entity_id=entity.id,
            ),
            Tax(
                name="Input Vat",
                code="INPT",
                account_id=account.id,
                rate=5,
                entity_id=entity2.id,
            ),
        ]
    )
    session.commit()

    taxes = session.scalars(select(Tax)).all()

    assert len(taxes) == 1
    assert taxes[0].code == "OTPT"
    assert taxes[0].rate == 10
    assert taxes[0].entity.name == "Test Entity"

    tax2 = session.get(Tax, 2)
    assert tax2 == None

    session.entity = entity2
    taxes = session.scalars(select(Tax)).all()

    assert len(taxes) == 1
    assert taxes[0].code == "INPT"
    assert taxes[0].rate == 5
    assert taxes[0].entity.name == "Test Entity Two"

    tax1 = session.get(Tax, 1)
    assert tax1 == None


def test_tax_recycling(session, entity, currency):
    """Tests the deleting, restoring and destroying functions of the tax model"""

    account = Account(
        name="test tax account",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )

    session.add(account)
    session.flush()

    tax = Tax(
        name="Output Vat",
        code="OTPT",
        account_id=account.id,
        rate=10,
        entity_id=entity.id,
    )
    session.add(tax)
    session.flush()

    tax_id = tax.id

    session.delete(tax)

    tax = session.get(Tax, tax_id)
    assert tax == None

    tax = session.get(Tax, tax_id, include_deleted=True)
    assert tax != None
    session.restore(tax)

    tax = session.get(Tax, tax_id)
    assert tax != None

    session.destroy(tax)

    tax = session.get(Tax, tax_id)
    assert tax == None

    tax = session.get(Tax, tax_id, include_deleted=True)
    assert tax != None
    session.restore(tax)  # destroyed models canot be restored

    tax = session.get(Tax, tax_id)
    assert tax == None
