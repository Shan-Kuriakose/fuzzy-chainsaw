"""The application layer of saving and reproducing dataset configurations.

Saving generates the dataset server-side from its configuration, count and
seed, and stores the canonical serialization bytes the engine emitted.
Reproducing loads those bytes and replays them through the engine, which
already refuses loudly when the regenerated records are not the saved ones —
the exact-record guarantee is enforced by tested engine code, never rebuilt
here.
"""

from datetime import datetime, timezone

from persona_engine import GenerationConfig, PersonaGenerator
from persona_engine import serialization
from persona_engine.dataset import GeneratedDataset
from persona_engine.serialization import DatasetManifest

from app.settings import Settings
from app.storage.database import (
    build_engine,
    build_session_factory,
    apply_migrations,
)
from app.storage.repository import (
    DatasetConfigurationRepository,
    SavedDatasetConfiguration,
    SqlAlchemyDatasetConfigurationRepository,
)


class InvalidDatasetConfiguration(ValueError):
    """Refused: the engine will not generate a dataset from this configuration."""


class DatasetConfigurationReplayRefused(ValueError):
    """Refused: a saved manifest no longer replays to its own saved rows."""


class DatasetConfigurationsService:
    """Save and reproduce named dataset configurations, scoped by team."""

    def __init__(self, repository: DatasetConfigurationRepository):
        self._repository = repository

    @classmethod
    def build_for(cls, settings: Settings) -> "DatasetConfigurationsService":
        """Build the service over the database the settings name.

        Building applies the versioned migrations first, so the store the
        service uses is always the schema the migrations describe.
        """

        engine = build_engine(settings.database_url)
        apply_migrations(str(engine.url))
        return cls(
            SqlAlchemyDatasetConfigurationRepository(build_session_factory(engine))
        )

    def save(
        self,
        team: str,
        name: str,
        configuration: dict,
        count: int,
        seed: int,
    ) -> None:
        """Generate and store the dataset the configuration describes.

        Refuses loudly with ``DuplicateDatasetConfiguration`` when the
        team already holds a configuration of that name, and with
        ``InvalidDatasetConfiguration`` when the engine refuses the
        configuration itself.
        """

        dataset = self._generate_dataset(configuration, count, seed)
        self._repository.save(
            SavedDatasetConfiguration(
                team=team,
                name=name,
                seed=seed,
                count=count,
                created_at=datetime.now(timezone.utc),
                manifest=serialization.to_json_bytes(dataset),
            )
        )

    def reproduce(self, team: str, name: str) -> dict:
        """Regenerate the exact records the saved configuration produced."""

        manifest = self._manifest_of(team, name)
        replayed = self._replayed(manifest)
        return {
            "seed": manifest.seed,
            "count": manifest.count,
            "personas": [persona.to_payload() for persona in replayed.personas],
        }

    def describe(self, team: str, name: str) -> dict:
        saved = self._required(self._repository.find_in_team(team, name))
        return self._described(saved)

    def list_in_team(self, team: str) -> list[dict]:
        return [
            self._described(saved) for saved in self._repository.list_in_team(team)
        ]

    def _manifest_of(self, team: str, name: str) -> DatasetManifest:
        saved = self._required(self._repository.find_in_team(team, name))
        return serialization.manifest_from_bytes(saved.manifest)

    def _replayed(self, manifest: DatasetManifest) -> GeneratedDataset:
        try:
            return serialization.replay(manifest)
        except ValueError as refused:
            raise DatasetConfigurationReplayRefused(str(refused)) from refused

    def _required(
        self, saved: SavedDatasetConfiguration | None
    ) -> SavedDatasetConfiguration:
        if saved is None:
            raise LookupError("no dataset configuration is saved under this name")
        return saved

    def _described(self, saved: SavedDatasetConfiguration) -> dict:
        manifest = serialization.manifest_from_bytes(saved.manifest)
        return {
            "name": saved.name,
            "team": saved.team,
            "seed": manifest.seed,
            "count": manifest.count,
            "configuration": dict(manifest.configuration),
            "created_at": saved.created_at,
        }

    def _generate_dataset(
        self, configuration: dict, count: int, seed: int
    ) -> GeneratedDataset:
        try:
            validated = GenerationConfig.from_payload(configuration)
        except (ValueError, KeyError, TypeError) as refused:
            raise InvalidDatasetConfiguration(str(refused)) from refused
        try:
            return PersonaGenerator().generate_dataset(
                validated, count=count, seed=seed
            )
        except ValueError as refused:
            raise InvalidDatasetConfiguration(str(refused)) from refused
