"""Dataset configuration persistence: a port and a SQLAlchemy adapter.

The service depends on the port; every concrete concern (database,
sessions, table identity) lives in the adapter behind it.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from app.storage.database import DatabaseSession
from app.storage.models import DatasetConfiguration


@dataclass(frozen=True)
class SavedDatasetConfiguration:
    """A dataset configuration as it is stored, independent of the database."""

    team: str
    name: str
    seed: int
    count: int
    created_at: datetime
    manifest: bytes


class DuplicateDatasetConfiguration(ValueError):
    """Raised when a name is saved a second time within the same team."""


class DatasetConfigurationRepository(ABC):
    """Persistence port for saved dataset configurations."""

    @abstractmethod
    def save(self, configuration: SavedDatasetConfiguration) -> None:
        """Store a configuration under its (team, name).

        Refuses loudly with ``DuplicateDatasetConfiguration`` when the
        team already holds a configuration of that name, so a refused
        save never resembles a successful one.
        """

    @abstractmethod
    def find_in_team(
        self, team: str, name: str
    ) -> SavedDatasetConfiguration | None:
        """Return the stored configuration of one name, or ``None``."""

    @abstractmethod
    def list_in_team(self, team: str) -> list[SavedDatasetConfiguration]:
        """Return every configuration stored for the team, by name."""


class SqlAlchemyDatasetConfigurationRepository(DatasetConfigurationRepository):
    """The adapter that keeps configuration state in a relational database."""

    def __init__(self, database_session: DatabaseSession):
        self._database_session = database_session

    def save(self, configuration: SavedDatasetConfiguration) -> None:
        with self._database_session() as session, session.begin():
            self._refuse_duplicate_names(session, configuration)
            session.add(self._as_new_row(configuration))

    def find_in_team(
        self, team: str, name: str
    ) -> SavedDatasetConfiguration | None:
        row = self._row_of(self._named_select(team, name))
        return self._as_saved_configuration(row) if row else None

    def list_in_team(self, team: str) -> list[SavedDatasetConfiguration]:
        with self._database_session() as session:
            rows = session.scalars(
                self._select_of_table().where(
                    DatasetConfiguration.team == team
                ).order_by(DatasetConfiguration.name)
            ).all()
            return [self._as_saved_configuration(row) for row in rows]

    def _named_select(self, team: str, name: str):
        return self._select_of_table().where(
            DatasetConfiguration.team == team,
            DatasetConfiguration.name == name,
        )

    def _select_of_table(self):
        return select(DatasetConfiguration)

    def _row_of(self, selection):
        with self._database_session() as session:
            return session.scalars(selection).first()

    def _refuse_duplicate_names(
        self, session, configuration: SavedDatasetConfiguration
    ) -> None:
        existing = session.scalars(
            self._named_select(configuration.team, configuration.name)
        ).first()
        if existing is not None:
            raise DuplicateDatasetConfiguration(
                f"a configuration named {configuration.name!r} is already "
                f"saved for team {configuration.team!r}"
            )

    def _as_new_row(
        self, configuration: SavedDatasetConfiguration
    ) -> DatasetConfiguration:
        return DatasetConfiguration(
            team=configuration.team,
            name=configuration.name,
            seed=configuration.seed,
            count=configuration.count,
            created_at=configuration.created_at,
            manifest=configuration.manifest,
        )

    def _as_saved_configuration(
        self, row: DatasetConfiguration
    ) -> SavedDatasetConfiguration:
        return SavedDatasetConfiguration(
            team=row.team,
            name=row.name,
            seed=row.seed,
            count=row.count,
            created_at=row.created_at,
            manifest=row.manifest,
        )
