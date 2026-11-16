"""Tests of the storage infrastructure behind dataset configurations.

The acceptance tests exercise the service and the API against the happy
paths; these cover the loud refusals the standard demands when the
persistence layer is misconfigured, and the repository's persistence
behavior directly.
"""

"""Tests of the storage infrastructure behind dataset configurations.

The acceptance tests exercise the service and the API against the happy
paths; these cover the loud refusals the standard demands when the
persistence layer is misconfigured, and the repository's persistence
behavior directly.
"""

from pathlib import Path

import pytest

ATLAS_TEAM = "atlas"
SAVED_NAME = "atlas-baseline"

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _service_over(tmp_path):
    from app.dataset_configurations.service import DatasetConfigurationsService
    from app.settings import Settings

    settings = Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'infrastructure.db'}",
    )
    return DatasetConfigurationsService.build_for(settings), settings


def _sample_configuration():
    return {
        "age_range": [25, 45],
        "genders": ["Female", "Male"],
        "geographies": ["Region North"],
        "income_range": [30_000, 90_000],
    }


def test_a_service_build_refuses_to_start_without_a_database_url():
    from app.dataset_configurations.service import DatasetConfigurationsService
    from app.settings import Settings

    unconfigured = Settings(app_name="fuzzy-chain-saw", environment="test")

    with pytest.raises(RuntimeError):
        DatasetConfigurationsService.build_for(unconfigured)


def test_settings_resolve_the_database_url_from_the_environment(monkeypatch):
    from app.settings import Settings

    monkeypatch.setenv("APP_NAME", "fuzzy-chain-saw")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://db.example.internal/fcs")

    settings = Settings()

    assert settings.database_url == "postgresql+psycopg://db.example.internal/fcs"


def test_migrations_refuse_to_run_without_a_database_url(monkeypatch):
    from alembic import command
    from alembic.config import Config

    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError):
        command.upgrade(alembic_config, "head")


def test_migrations_run_offline_and_emit_sql(monkeypatch):
    from alembic import command
    from alembic.config import Config

    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    command.upgrade(alembic_config, "0001", sql=True)


def test_the_repository_persists_a_configuration_for_later_find(tmp_path):
    service, _ = _service_over(tmp_path)
    from app.dataset_configurations.service import DatasetConfigurationsService

    service.save(ATLAS_TEAM, SAVED_NAME, _sample_configuration(), 10, 42)

    reread = DatasetConfigurationsService.build_for(
        _settings_over(tmp_path)
    ).describe(ATLAS_TEAM, SAVED_NAME)

    assert reread["name"] == SAVED_NAME
    assert reread["seed"] == 42
    assert reread["count"] == 10
    assert reread["configuration"] == _sample_configuration()


def test_the_repository_lists_only_the_requested_team(tmp_path):
    service, _ = _service_over(tmp_path)
    service.save(ATLAS_TEAM, SAVED_NAME, _sample_configuration(), 10, 42)
    service.save("helios", "helios-baseline", _sample_configuration(), 5, 7)

    listed = service.list_in_team(ATLAS_TEAM)

    assert [entry["name"] for entry in listed] == [SAVED_NAME]


def _settings_over(tmp_path):
    from app.settings import Settings

    return Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'infrastructure.db'}",
    )
