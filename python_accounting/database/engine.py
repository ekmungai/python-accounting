import os
from sqlalchemy import create_engine

directory, _ = os.path.split(os.path.realpath(__file__))
database = os.path.join(directory, "accounting.sqlite")
engine = create_engine(f"sqlite:///{database}", echo=True).execution_options(
    include_deleted=False, ignore_isolation=False
)
