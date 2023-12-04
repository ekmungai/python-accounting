import pytest
from datetime import datetime
from .conftest import engine, entity, session
from sqlalchemy import select
from python_accounting.models import Account


# def test_account_entity(entity, session):
#     """Tests the relationship between an account and its associated entity"""
#     account = Account(
#         calendar_year=datetime.today().year + 1, period_count=2, entity_id=entity.id
#     )
#     session.add(account)
#     session.commit()

#     account = session.get(Account, account.id)
#     assert account.entity.name == "Test Entity"


# def test_account_validation(session, entity):
#     """Tests the validation of reporting period objects"""
#     with pytest.raises(DuplicateAccountError):
#         session.add(
#             Account(
#                 calendar_year=datetime.today().year, period_count=1, entity_id=entity.id
#             )
#         )


# def test_account_isolation(session, entity):
#     """Tests the isolation of reporting period objects by entity"""

#     year = datetime.today().year
#     entity2 = Entity(name="Test Entity Two")
#     session.add(entity2)
#     session.flush()
#     entity2 = session.get(Entity, entity2.id)

#     session.add_all(
#         [
#             Account(
#                 calendar_year=year - 1, period_count=1, entity_id=entity.id
#             ),
#             Account(
#                 calendar_year=year,
#                 period_count=2,
#                 entity_id=entity2.id,
#             ),
#         ]
#     )
#     session.commit()

#     accounts = session.scalars(select(Account)).all()

#     assert len(accounts) == 2
#     assert accounts[0].calendar_year == year
#     assert accounts[0].period_count == 1
#     assert accounts[0].entity.name == "Test Entity"

#     account2 = session.get(Account, 3)
#     assert account2 == None

#     session.entity = entity2
#     accounts = session.scalars(select(Account)).all()

#     assert len(accounts) == 1
#     assert accounts[0].calendar_year == year
#     assert accounts[0].period_count == 2
#     assert accounts[0].entity.name == "Test Entity Two"

#     account1 = session.get(Account, 1)
#     assert account1 == None


# def test_account_recycling(session, entity):
#     """Tests the deleting, restoring and destroying functions of the account model"""

#     account = Account(
#         calendar_year=datetime.today().year - 1, period_count=1, entity_id=entity.id
#     )
#     session.add(account)
#     session.flush()

#     account_id = account.id

#     session.delete(account)

#     account = session.get(Account, account_id)
#     assert account == None

#     account = session.get(
#         Account, account_id, include_deleted=True
#     )
#     assert account != None
#     session.restore(account)

#     account = session.get(Account, account_id)
#     assert account != None

#     session.destroy(account)

#     account = session.get(Account, account_id)
#     assert account == None

#     account = session.get(
#         Account, account_id, include_deleted=True
#     )
#     assert account != None
#     session.restore(account)  # destroyed models canot be restored

#     account = session.get(Account, account_id)
#     assert account == None


# def test_account_dates(entity):
#     """Tests the calculation of account start and end dates"""

#     assert Account.date_year() == datetime.today().year
#     assert (
#         Account.date_year(
#             datetime.strptime("2025-06-03", "%Y-%m-%d"), entity
#         )
#         == 2025
#     )

#     period_span = Account.period_span(
#         datetime.strptime("2025-06-03", "%Y-%m-%d"), entity
#     )
#     assert period_span["period_start"] == datetime(2025, 1, 1, 0, 0, 0)
#     assert period_span["period_end"] == datetime(2025, 12, 31, 23, 59, 59)

#     entity.year_start = 4

#     assert (
#         Account.date_year(
#             datetime.strptime("2025-03-03", "%Y-%m-%d"), entity
#         )
#         == 2024
#     )
#     period_span = Account.period_span(
#         datetime.strptime("2025-03-03", "%Y-%m-%d"), entity
#     )
#     assert period_span["period_start"] == datetime(2024, 4, 1, 0, 0, 0)
#     assert period_span["period_end"] == datetime(2025, 3, 31, 23, 59, 59)


# def test_account_from_date(session, entity):
#     """Tests the retrieval of the account for a given date"""

#     with pytest.raises(MissingAccountError):
#         Account.get_period(
#             datetime.strptime("2025-03-03", "%Y-%m-%d"), entity, session
#         )

#     Account.get_period(
#         datetime.today(), entity, session
#     ) == entity.account
