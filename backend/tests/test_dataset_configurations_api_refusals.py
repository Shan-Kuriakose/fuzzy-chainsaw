"""API-level refusal tests for saving and reproducing dataset configurations.

The refusals the engine raises while saving or replaying a dataset reach
the API as explained 4xx responses, never as an unexplained server
error: the QA user is told which boundary the engine refused and what
failed during a replay.
"""

import json
import sqlite3

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


def _client_over(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.settings import Settings

    settings = Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'dataset-configurations.db'}",
    )
    return TestClient(create_app(settings=settings))


def _save_configuration(client, **overrides):
    payload = {
        "name": SAVED_NAME,
        "count": SAVED_COUNT,
        "seed": SAVED_SEED,
        "configuration": SAVED_CONFIGURATION,
    }
    payload.update(overrides)
    return client.put(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations", json=payload
    )


def _tamper_stored_manifest(tmp_path, alteration):
    import importlib

    serialization = importlib.import_module("persona_engine.serialization")
    from persona_engine import GenerationConfig, PersonaGenerator

    dataset = PersonaGenerator().generate_dataset(
        GenerationConfig.from_payload(SAVED_CONFIGURATION),
        count=SAVED_COUNT,
        seed=SAVED_SEED,
    )
    manifest = json.loads(serialization.to_json_bytes(dataset))
    alteration(manifest)
    tampered_bytes = json.dumps(
        manifest, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    with sqlite3.connect(str(tmp_path / "dataset-configurations.db")) as connection:
        connection.execute(
            "UPDATE dataset_configurations SET manifest = ? WHERE name = ?",
            (tampered_bytes, SAVED_NAME),
        )
        connection.commit()


def test_saving_a_configuration_the_engine_refuses_is_refused_with_its_reason(
    tmp_path,
):
    client = _client_over(tmp_path)

    refused_save = _save_configuration(
        client, configuration={**SAVED_CONFIGURATION, "genders": ["Female", "Female"]}
    )

    assert refused_save.status_code == 422, refused_save.text
    assert "duplicate" in refused_save.text, refused_save.text


def test_saving_a_configuration_with_a_boundary_key_missing_is_refused(tmp_path):
    client = _client_over(tmp_path)
    incomplete_configuration = {
        key: value for key, value in SAVED_CONFIGURATION.items() if key != "geographies"
    }

    refused_save = _save_configuration(
        client, configuration=incomplete_configuration
    )

    assert refused_save.status_code == 422, refused_save.text
    assert "geographies" in refused_save.text, refused_save.text


def test_reproducing_rows_that_diverge_from_the_saved_ones_is_refused(tmp_path):
    client = _client_over(tmp_path)
    setup_save = _save_configuration(client)
    assert setup_save.status_code == 201, setup_save.text

    def corrupt_the_first_row(manifest):
        manifest["personas"][0]["first_name"] = "Tampered"

    _tamper_stored_manifest(tmp_path, corrupt_the_first_row)

    reproduction = client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations/{SAVED_NAME}/reproduce"
    )

    assert reproduction.status_code == 409, reproduction.text
    assert "not the saved ones" in reproduction.text, reproduction.text


def test_reproducing_a_dataset_of_an_unsupported_manifest_version_is_refused(
    tmp_path,
):
    client = _client_over(tmp_path)
    setup_save = _save_configuration(client)
    assert setup_save.status_code == 201, setup_save.text

    def age_the_manifest_version(manifest):
        manifest["manifest_version"] = manifest["manifest_version"] + 1

    _tamper_stored_manifest(tmp_path, age_the_manifest_version)

    reproduction = client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations/{SAVED_NAME}/reproduce"
    )

    assert reproduction.status_code == 409, reproduction.text
    assert "manifest version" in reproduction.text, reproduction.text
