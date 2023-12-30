from .engine import engine
import python_accounting.models as models


def database_init() -> None:
    models.Base.metadata.create_all(engine)
