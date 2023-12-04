import pytest
from sqlalchemy import create_engine
import python_accounting.models as models
from python_accounting.database.session import Session


@pytest.fixture
def engine():
    engine = create_engine(f"sqlite://", echo=False)
    models.Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def entity(session):
    entity = models.Entity(name="Test Entity")
    session.add(entity)
    session.commit()
    return session.get(models.Entity, entity.id)
