from .engine import engine
import python_accounting.models as models


def database_init():
    models.Base.metadata.create_all(engine)
