import pytest
from datetime import datetime
from .conftest import engine, entity, session
from sqlalchemy import select
from python_accounting.models import Account, Category, Entity
from python_accounting.exceptions import InvalidAccountTypeError


def test_category_entity(entity, session):
    """Tests the relationship between a category and its associated entity"""
    category = Category(
        name="Test Category",
        category_account_type=Account.AccountType.BANK,
        entity_id=entity.id,
    )
    session.add(category)
    session.commit()

    category = session.get(Category, category.id)
    assert category.entity.name == "Test Entity"


def test_category_validation(session, entity):
    """Tests the validation of category objects"""
    with pytest.raises(InvalidAccountTypeError):
        session.add(
            Category(
                name="Test Category",
                category_account_type="Accont Type",
                entity_id=entity.id,
            )
        )


def test_category_isolation(session, entity):
    """Tests the isolation of category objects by entity"""

    entity2 = Entity(name="Test Entity Two")
    session.add(entity2)
    session.flush()
    entity2 = session.get(Entity, entity2.id)

    session.add_all(
        [
            Category(
                name="Test Category One",
                category_account_type=Account.AccountType.BANK,
                entity_id=entity.id,
            ),
            Category(
                name="Test Category Two",
                category_account_type=Account.AccountType.RECEIVABLE,
                entity_id=entity2.id,
            ),
        ]
    )
    session.commit()

    categories = session.scalars(select(Category)).all()

    assert len(categories) == 1
    assert categories[0].name == "Test Category One"
    assert categories[0].category_account_type == Account.AccountType.BANK
    assert categories[0].entity.name == "Test Entity"

    category2 = session.get(Category, 2)
    assert category2 == None

    session.entity = entity2
    categories = session.scalars(select(Category)).all()

    assert len(categories) == 1
    assert categories[0].name == "Test Category Two"
    assert categories[0].category_account_type == Account.AccountType.RECEIVABLE
    assert categories[0].entity.name == "Test Entity Two"

    category1 = session.get(Category, 1)
    assert category1 == None


def test_category_recycling(session, entity):
    """Tests the deleting, restoring and destroying functions of the category model"""

    category = Category(
        name="Test Category One",
        category_account_type=Account.AccountType.BANK,
        entity_id=entity.id,
    )
    session.add(category)
    session.flush()

    category_id = category.id

    session.delete(category)

    category = session.get(Category, category_id)
    assert category == None

    category = session.get(Category, category_id, include_deleted=True)
    assert category != None
    session.restore(category)

    category = session.get(Category, category_id)
    assert category != None

    session.destroy(category)

    category = session.get(Category, category_id)
    assert category == None

    category = session.get(Category, category_id, include_deleted=True)
    assert category != None
    session.restore(category)  # destroyed models canot be restored

    category = session.get(Category, category_id)
    assert category == None


# def test_account_balances(session, entity): TODO
#     """Tests the aggregation of account balances by category"""

#     with pytest.raises(MissingCategoryError):
#         Category.get_period(
#             datetime.strptime("2025-03-03", "%Y-%m-%d"), entity, session
#         )

#     Category.get_period(datetime.today(), entity, session) == entity.category
