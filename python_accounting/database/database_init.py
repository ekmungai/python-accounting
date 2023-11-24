from .engine import engine
import models


def database_init():
    models.Base.metadata.create_all(engine)
