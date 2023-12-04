from sqlalchemy import create_engine
from python_accounting.config import config


database = config["database"]
engine = create_engine(database["url"], echo=database["echo"]).execution_options(
    include_deleted=database["include_deleted"],
    ignore_isolation=database["ignore_isolation"],
)
