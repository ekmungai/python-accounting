import peewee

from . import BaseModel
from . import Entity


class RecycledModel(BaseModel):
    """This is the python (peewee) representation of the recycled table"""

    id = peewee.AutoField()
    name = peewee.CharField()
    code = peewee.CharField(max_length=3)

    entity = peewee.ForeignKeyField(Entity, backref="entity")

    class Meta:
        table_name = "currency"
