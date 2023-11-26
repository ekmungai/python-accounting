from sqlalchemy.orm.session import Session
from sqlalchemy import event, orm, true
from datetime import datetime

from python_accounting.models import Recycled, Entity
from python_accounting.mixins import RecyclingMixin, IsolatingMixin
from python_accounting.exceptions import MissingEntityError


def _filter_options(execute_state, option):
    """Valiadate if filter should be applied"""
    return (
        not execute_state.is_column_load
        and not execute_state.is_relationship_load
        and not execute_state.execution_options.get(option, False)
        and not execute_state.session.info.get(option, False)
    )


class AccountingSession(Session):
    entity: Entity

    def __init__(self, bind=None, info=None):
        super(AccountingSession, self).__init__(bind=bind, info=info)

    @event.listens_for(Session, "transient_to_pending")
    def _set_session_entity(session, object_):
        """Make sure that all objects have an associated Entity"""

        if hasattr(session, "entity") and session.entity is not None:
            return

        if isinstance(object_, Entity):
            session.entity = object_
        elif object_.entity_id is None:
            raise MissingEntityError
        else:
            session.entity = session.get(Entity, object_.entity_id)

    @event.listens_for(Session, "do_orm_execute")
    def _add_filtering_criteria(execute_state):
        """Intercept all ORM queries to filter objects by delete status and entity id"""

        # Recycling filter
        if _filter_options(execute_state, "include_deleted"):
            execute_state.statement = execute_state.statement.options(
                orm.with_loader_criteria(
                    RecyclingMixin,
                    lambda cls: cls.is_deleted != true(),
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

    def delete(self, instance):
        """Override the delete method to enable recycling"""

        if instance.id == self.entity.id:
            print("watchudoin mayn!!")
        # instance.deleted_at = datetime.now()
        # self.add(
        #     Recycled(
        #         recycled_type=str(instance.__class__),
        #         recycled_id=instance.id,
        #         entity_id=instance.entity_id,
        #     )
        # )


def Session(engine):
    """Construct the accounting session"""
    return AccountingSession(
        bind=engine,
        info={
            "include_deleted": engine.get_execution_options().get(
                "include_deleted", False
            ),
            "ignore_isolation": engine.get_execution_options().get(
                "ignore_isolation", False
            ),
        },
    )
