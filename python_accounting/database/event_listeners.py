# event_listeners.py

"""
This module contains event listeners that are attached to the SQLAlchemy Session object.
"""
from typing import List
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm.query import Query
from sqlalchemy.orm.session import Session as SessionType
from sqlalchemy.orm.state import InstanceState
from sqlalchemy.sql.selectable import Select

from python_accounting.config import config
from python_accounting.models import (
    Entity,
    Transaction,
    Assignment,
    Account,
    Tax,
    LineItem,
    Balance,
    ReportingPeriod,
)
from python_accounting.reports import BalanceSheet
from python_accounting.transactions import ClientInvoice, JournalEntry


def _add_filtering_criteria(execute_state):
    """
    Adds a filtering criteria to all queries to ensure that only data for the current entity is returned.
    """
    if (
        execute_state.is_select
        and not execute_state.is_column_load
        and not execute_state.is_relationship_load
    ):
        entity_id = (
            execute_state.session.entity.id if execute_state.session.entity else None
        )
        execute_state.statement = execute_state.statement.options(
            Query.selectable_entity_from_alias_callable(
                lambda alias: (
                    alias.filter(alias.original.entity_id == entity_id)
                    if issubclass(alias.original.class_, Entity)
                    and hasattr(alias.original.class_, "entity_id")
                    else alias.original
                )
            )
        )


def _before_flush(session: SessionType, flush_context, instances):
    """
    Processes the session objects before they are flushed to the database.
    """
    if session.entity:
        # New objects
        for obj in session.new:
            if isinstance(obj, Entity):
                obj.entity_id = session.entity.id
            if isinstance(obj, Transaction):
                obj.process_posting(session)
            if isinstance(obj, Assignment):
                obj.process_assignment(session)

        # updated objects
        for obj in session.dirty:
            if isinstance(obj, Transaction):
                state: InstanceState = session.identity_map.get_state_for(obj)
                if "credited_account_id" in state.committed_state or (
                    "debited_account_id" in state.committed_state
                ):
                    obj.revert_posting(session)
                    obj.process_posting(session)
            if isinstance(obj, Assignment):
                obj.process_assignment(session)

        # deleted objects
        for obj in session.deleted:
            if isinstance(obj, Transaction):
                obj.revert_posting(session)
            if isinstance(obj, Assignment):
                obj.revert_assignment(session)


def _after_flush(session: SessionType, flush_context):
    """
    Processes the session objects after they have been flushed to the database.
    """
    if session.entity:
        for obj in flush_context.stale_session_new:
            if isinstance(obj, Account):
                obj.get_balance(session)
            if isinstance(obj, Tax):
                obj.get_balance(session)
            if isinstance(obj, LineItem):
                obj.tax.get_balance(session)
            if isinstance(obj, Assignment):
                obj.transaction.account.get_balance(session)
                if isinstance(obj.transaction, ClientInvoice):
                    obj.transaction.get_balance(session)
            if isinstance(obj, JournalEntry):
                obj.line_items[0].account.get_balance(session)
                obj.line_items[1].account.get_balance(session)

        for obj in session.deleted:
            if isinstance(obj, Transaction):
                obj.account.get_balance(session)
            if isinstance(obj, Assignment):
                obj.transaction.account.get_balance(session)
                if isinstance(obj.transaction, ClientInvoice):
                    obj.transaction.get_balance(session)


def register_accounting_event_listeners(session_class: type[Session]):
    """
    Registers the event listeners for the accounting session.
    """
    event.listen(session_class, "do_orm_execute", _add_filtering_criteria)
    event.listen(session_class, "before_flush", _before_flush)
    event.listen(session_class, "after_flush", _after_flush)
