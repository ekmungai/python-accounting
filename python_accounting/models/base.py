from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr


class Base(DeclarativeBase):
    """The database model base class"""

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now())
    deleted_at: Mapped[datetime] = mapped_column(nullable=True)
    destroyed_at: Mapped[datetime] = mapped_column(nullable=True)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
