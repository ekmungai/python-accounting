from datetime import datetime

from sqlalchemy.orm.session import Session
from sqlalchemy import event, orm, and_

from python_accounting.models import Entity, Recyclable
from python_accounting.mixins import IsolatingMixin
from python_accounting.exceptions import MissingEntityError


def _filter_options(execute_state, option):
    """Valiadate if filter should be applied"""
    return (
        not execute_state.is_column_load
        and not execute_state.is_relationship_load
        and not execute_state.execution_options.get(option, False)
        and not execute_state.session.info.get(option, False)
    )


class EventListenersMixin:
    """This class provides logic for handling events in sqlalchemy's orm lifecycle"""

    @event.listens_for(Session, "transient_to_pending")
    def _set_session_entity(session, object_):
        """Make sure that all objects have an associated Entity"""

        if not hasattr(session, "entity") or session.entity is None:
            if isinstance(object_, Entity):
                session.entity = object_
            elif object_.entity_id is None:
                raise MissingEntityError
            else:
                session.entity = session.get(Entity, object_.entity_id)

        if (
            session.entity.reporting_period is None
            or session.entity.reporting_period.calendar_year != datetime.today().year
        ):
            session._set_reporting_period()

    @event.listens_for(Session, "do_orm_execute")
    def _add_filtering_criteria(execute_state):
        """Intercept all ORM queries to filter objects by delete status and entity id"""

        # Recycling filter
        if _filter_options(execute_state, "include_deleted"):
            execute_state.statement = execute_state.statement.options(
                orm.with_loader_criteria(
                    Recyclable,
                    lambda cls: and_(cls.deleted_at == None, cls.destroyed_at == None),
                    include_aliases=True,
                )
            )

        # Entity filter
        if (
            _filter_options(execute_state, "ignore_isolation")
            and execute_state.statement.column_descriptions[0]["type"] is not Entity
        ):
            session_entity_id = execute_state.session.entity.id
            execute_state.statement = execute_state.statement.options(
                orm.with_loader_criteria(
                    IsolatingMixin,
                    lambda cls: cls.entity_id == session_entity_id,
                    include_aliases=True,
                )
            )

    @event.listens_for(Session, "before_attach")
    def _validate_model(session, object_):
        """Run validation logic against the model instance if any"""

        if hasattr(object_, "validate"):
            object_.validate(session)
