"""Acceptance and refusal tests for the programmatic export endpoint.

Each test maps to an acceptance criterion of the story:
AC4 - a saved configuration is exported through the API in CSV or JSON,
      with exactly the bytes the engine's own export emits; any other
      format is refused with an explained 422 and an unsaved name is 404
"""

ATLAS_TEAM = "atlas"

API_KEY = "atlas-pipeline-key"

SAVED_NAME = "atlas-export-baseline"
SAVED_COUNT = 9
SAVED_SEED = 42
SAVED_CONFIGURATION = {
    "age_range": [25, 45],
    "genders": ["Female", "Male"],
    "geographies": ["Region North"],
    "income_range": [30_000, 90_000],
}

AUTHORIZATION_HEADER = {"Authorization": f"Bearer {API_KEY}"}


def _client_over(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.settings import Settings

    settings = Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'dataset-export.db'}",
        api_key=API_KEY,
        forbidden_values_path=_forbidden_values_file(tmp_path),
    )
    return TestClient(create_app(settings=settings))


def _forbidden_values_file(tmp_path):
    path = tmp_path / "forbidden-values.txt"
    path.write_text(
        "Forsaken Region\nUnlisted Gender\n", encoding="utf-8"
    )
    return path


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


def _export(client, name=SAVED_NAME, format="csv"):
    return client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations/{name}/export",
        params={"format": format},
        headers=AUTHORIZATION_HEADER,
    )


def _engine_dataset(configuration, count, seed):
    from persona_engine import GenerationConfig, PersonaGenerator

    return PersonaGenerator().generate_dataset(
        GenerationConfig.from_payload(configuration),
        count=count,
        seed=seed,
    )


def test_exporting_a_saved_configuration_returns_csv_bytes_identical_to_the_engine_export(
    tmp_path,
):
    from persona_engine.serialization import to_csv_bytes

    client = _client_over(tmp_path)
    save_response = _save_configuration(client)
    assert save_response.status_code == 201, save_response.text

    exported = _export(client, format="csv")

    assert exported.status_code == 200, exported.text
    assert exported.content == to_csv_bytes(
        _engine_dataset(SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED)
    )
    assert exported.headers["content-type"].lower().startswith("text/csv")


def test_exporting_a_saved_configuration_returns_json_records_identical_to_the_engine_export(
    tmp_path,
):
    import json

    from persona_engine.serialization import to_json_records_bytes

    client = _client_over(tmp_path)
    save_response = _save_configuration(client)
    assert save_response.status_code == 201, save_response.text

    exported = _export(client, format="json")

    assert exported.status_code == 200, exported.text
    expected = to_json_records_bytes(
        _engine_dataset(SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED)
    )
    assert json.loads(exported.content) == json.loads(expected)
    assert exported.headers["content-type"].lower().startswith("application/json")


def test_exporting_in_any_other_format_is_refused_with_an_explained_error(tmp_path):
    client = _client_over(tmp_path)
    save_response = _save_configuration(client)
    assert save_response.status_code == 201, save_response.text

    refused = _export(client, format="parquet")

    assert refused.status_code == 422, refused.text
    assert "format" in refused.text, refused.text


def test_exporting_an_unsaved_name_is_refused(tmp_path):
    client = _client_over(tmp_path)

    refused = _export(client, name="atlas-never-saved")

    assert refused.status_code == 404, refused.text
    assert "no dataset configuration" in refused.text, refused.text
