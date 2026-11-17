"""Acceptance tests for the programmatic one-shot generation endpoint.

Each test maps to an acceptance criterion of the story:
AC1 - a valid authenticated request generates and returns the dataset
      directly in the requested format, and the records are the ones the
      engine draws from the same seed and configuration
AC2 - the API path applies the same identity-safety screening as the UI
      path: a configuration whose labels carry a forbidden value is
      refused, and the same refusal reaches the UI save path
"""

import json

ATLAS_TEAM = "atlas"

API_KEY = "atlas-pipeline-key"

GENERATED_COUNT = 12
GENERATED_SEED = 42
GENERATION_CONFIGURATION = {
    "age_range": [25, 45],
    "genders": ["Female", "Male"],
    "geographies": ["Region North"],
    "income_range": [30_000, 90_000],
}

# Values compliance could forbid: obviously synthetic placeholders that no
# happy-path configuration or generated record carries.
FORBIDDEN_GEOGRAPHY = "Forsaken Region"
FORBIDDEN_GENDER = "Unlisted Gender"

AUTHORIZATION_HEADER = {"Authorization": f"Bearer {API_KEY}"}


def _forbidden_values_file(tmp_path):
    path = tmp_path / "forbidden-values.txt"
    path.write_text(
        f"{FORBIDDEN_GEOGRAPHY}\n{FORBIDDEN_GENDER}\n", encoding="utf-8"
    )
    return path


def _client_over(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.settings import Settings

    settings = Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'generated-datasets.db'}",
        api_key=API_KEY,
        forbidden_values_path=_forbidden_values_file(tmp_path),
    )
    return TestClient(create_app(settings=settings))


def _generation_payload(**overrides):
    payload = {
        "count": GENERATED_COUNT,
        "seed": GENERATED_SEED,
        "format": "csv",
        "configuration": GENERATION_CONFIGURATION,
    }
    payload.update(overrides)
    return payload


def _generate_dataset(client, **overrides):
    return client.post(
        f"/api/teams/{ATLAS_TEAM}/generated-datasets",
        json=_generation_payload(**overrides),
        headers=AUTHORIZATION_HEADER,
    )


def _engine_dataset(configuration, count, seed):
    from persona_engine import GenerationConfig, PersonaGenerator

    return PersonaGenerator().generate_dataset(
        GenerationConfig.from_payload(configuration),
        count=count,
        seed=seed,
    )


def test_generating_a_dataset_returns_the_generated_dataset_for_a_valid_authenticated_request(
    tmp_path,
):
    from persona_engine.serialization import to_csv_bytes

    client = _client_over(tmp_path)

    generated = _generate_dataset(client)

    assert generated.status_code == 200, generated.text
    assert generated.content == to_csv_bytes(
        _engine_dataset(GENERATION_CONFIGURATION, GENERATED_COUNT, GENERATED_SEED)
    )


def test_generating_with_the_same_seed_and_configuration_matches_a_direct_engine_run(
    tmp_path,
):
    client = _client_over(tmp_path)

    generated = _generate_dataset(client, format="json")

    assert generated.status_code == 200, generated.text
    expected = [
        persona.to_payload()
        for persona in _engine_dataset(
            GENERATION_CONFIGURATION, GENERATED_COUNT, GENERATED_SEED
        ).personas
    ]
    assert json.loads(generated.content) == expected


def test_generating_refuses_a_configuration_whose_labels_carry_a_forbidden_value(
    tmp_path,
):
    client = _client_over(tmp_path)

    refused = _generate_dataset(
        client,
        configuration={
            **GENERATION_CONFIGURATION,
            "geographies": ["Region North", FORBIDDEN_GEOGRAPHY],
        },
    )

    assert refused.status_code == 422, refused.text
    assert FORBIDDEN_GEOGRAPHY.lower() in refused.text.lower(), refused.text


def test_the_ui_save_path_is_screened_identically_to_the_api_path(tmp_path):
    client = _client_over(tmp_path)

    refused_save = client.put(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations",
        json={
            "name": "atlas-screened-labels",
            "count": 5,
            "seed": 7,
            "configuration": {
                **GENERATION_CONFIGURATION,
                "genders": ["Female", FORBIDDEN_GENDER],
            },
        },
    )

    assert refused_save.status_code == 422, refused_save.text
    assert FORBIDDEN_GENDER.lower() in refused_save.text.lower(), refused_save.text
