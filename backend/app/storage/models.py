"""SQLAlchemy models of the tables this service owns."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

TABLE_NAME = "dataset_configurations"


class Base(DeclarativeBase):
    pass


class DatasetConfiguration(Base):
    """One saved dataset configuration and the dataset bytes it produced.

    The ``manifest`` column holds the canonical serialization of the
    dataset the configuration generated when it was saved, so reproduction
    replays exactly those bytes.
    """

    __tablename__ = TABLE_NAME
    __table_args__ = (
        UniqueConstraint("team", "name", name="uq_dataset_configurations_team_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team: Mapped[str] = mapped_column(String(length=64), nullable=False)
    name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    manifest: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
