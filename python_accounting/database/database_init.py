# database_init.py

from python_accounting.database.engine import engine
from python_accounting.database.session import AccountingSession
from python_accounting.database.base import Base
from python_accounting.database.event_listeners import register_accounting_event_listeners

def init_database():
    """
    Initialise the database and attach event listeners.
    """
    Base.metadata.create_all(bind=engine)
    register_accounting_event_listeners(AccountingSession)