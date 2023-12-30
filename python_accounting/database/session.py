from sqlalchemy.orm.session import Session

from python_accounting.models import Entity
from .session_overrides import SessionOverridesMixin
from .accounting_functions import AccountingFunctionsMixin
from .event_listeners import EventListenersMixin


class AccountingSession(
    SessionOverridesMixin, EventListenersMixin, AccountingFunctionsMixin, Session
):
    entity: Entity

    def __init__(self, bind=None, info=None) -> None:
        super(AccountingSession, self).__init__(bind=bind, info=info)


def Session(engine) -> Session:
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
