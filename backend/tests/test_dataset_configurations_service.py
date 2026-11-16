"""Service-level tests for saving and reproducing dataset configurations.

These name the refusals the service layer must raise before any
context-specific storage adapter is consulted: a duplicate name within a
team, an unsaved configuration, and a stored manifest that no longer
replays to its own rows.
"""

import json

import pytest

ATLAS_TEAM = "atlas"

SAVED_NAME = "atlas-baseline"
SAVED_COUNT = 10
SAVED_SEED = 42
SAVED_CONFIGURATION = {
    "age_range": [25, 45],
    "genders": ["Female", "Male"],
    "geographies": ["Region North"],
    "income_range": [30_000, 90_000],
}


def _service_over(tmp_path):
    from app.dataset_configurations.service import DatasetConfigurationsService
    from app.settings import Settings

    settings = Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'configurations.db'}",
    )
    return DatasetConfigurationsService.build_for(settings)


def _engine_rows_for_saved_configuration():
    from persona_engine import GenerationConfig, PersonaGenerator

    dataset = PersonaGenerator().generate_dataset(
        GenerationConfig.from_payload(SAVED_CONFIGURATION),
        count=SAVED_COUNT,
        seed=SAVED_SEED,
    )
    return [persona.to_payload() for persona in dataset.personas]


def _tamper_saved_manifest_rows(tmp_path):
    import sqlite3

    from persona_engine import serialization

    manifest = json.loads(serialization.to_json_bytes(_dataset()))
    manifest["personas"][0]["first_name"] = "Tampered"
    tampered = json.dumps(
        manifest, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")

    connection = sqlite3.connect(str(tmp_path / "configurations.db"))
    try:
        connection.execute(
            "UPDATE dataset_configurations SET manifest = ? WHERE name = ?",
            (sqlite3.Binary(tampered), SAVED_NAME),
        )
        connection.commit()
    finally:
        connection.close()


def _dataset():
    from persona_engine import GenerationConfig, PersonaGenerator

    return PersonaGenerator().generate_dataset(
        GenerationConfig.from_payload(SAVED_CONFIGURATION),
        count=SAVED_COUNT,
        seed=SAVED_SEED,
    )


def test_a_service_reproduces_a_dataset_from_its_saved_configuration(tmp_path):
    service = _service_over(tmp_path)

    service.save(ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED)

    reproduction = service.reproduce(ATLAS_TEAM, SAVED_NAME)

    assert reproduction["seed"] == SAVED_SEED
    assert reproduction["count"] == SAVED_COUNT
    assert reproduction["personas"] == _engine_rows_for_saved_configuration()


def test_a_service_refuses_a_second_save_of_a_name_within_a_team(tmp_path):
    service = _service_over(tmp_path)
    service.save(ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED)

    with pytest.raises(ValueError):
        service.save(ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, 6, SAVED_SEED + 1)


def test_a_service_refuses_reproducing_a_configuration_no_one_saved(tmp_path):
    service = _service_over(tmp_path)

    with pytest.raises(LookupError):
        service.reproduce(ATLAS_TEAM, SAVED_NAME)


def test_a_service_refuses_a_saved_manifest_that_no_longer_replays_to_its_own_rows(
    tmp_path,
):
    service = _service_over(tmp_path)
    service.save(ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED)
    _tamper_saved_manifest_rows(tmp_path)

    with pytest.raises(ValueError, match="not the saved ones"):
        service.reproduce(ATLAS_TEAM, SAVED_NAME)
