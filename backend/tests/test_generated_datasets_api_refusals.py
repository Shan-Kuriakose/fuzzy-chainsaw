"""Refusal tests for the programmatic generation endpoint.

The endpoint refuses loudly and with an explanation: a missing or wrong
bearer key is 401, an unconfigured key is 503 on use, an unsupported
export format and an out-of-bounds count or seed are explained 422s.
The configured key never appears in any response.
"""

from app.routes.dataset_configurations import MAXIMUM_DATASET_RECORDS
from app.storage.models import (
    MAXIMUM_STORED_INTEGER,
)

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


def _forbidden_values_file(tmp_path):
    path = tmp_path / "forbidden-values.txt"
    path.write_text(
        "Forsaken Region\nUnlisted Gender\n", encoding="utf-8"
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


def _client_without_a_configured_api_key(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.settings import Settings

    settings = Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'generation-unauthenticated.db'}",
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


def _generate_with(client, headers=None, **overrides):
    return client.post(
        f"/api/teams/{ATLAS_TEAM}/generated-datasets",
        json=_generation_payload(**overrides),
        headers=headers,
    )


def test_a_request_without_a_bearer_key_is_refused(tmp_path):
    client = _client_over(tmp_path)

    refused = _generate_with(client)

    assert refused.status_code == 401, refused.text
    assert API_KEY not in refused.text, refused.text


def test_a_request_with_a_wrong_bearer_key_is_refused(tmp_path):
    client = _client_over(tmp_path)

    wrong_key = "some-other-teams-key"
    refused = _generate_with(
        client, headers={"Authorization": f"Bearer {wrong_key}"}
    )

    assert refused.status_code == 401, refused.text
    assert API_KEY not in refused.text, refused.text
    assert wrong_key not in refused.text, refused.text


def test_generation_without_a_configured_api_key_fails_loudly(tmp_path):
    client = _client_without_a_configured_api_key(tmp_path)

    unauthenticated = _generate_with(
        client, headers={"Authorization": "Bearer whatever-key"}
    )

    assert unauthenticated.status_code == 503, unauthenticated.text


def test_out_of_bounds_count_or_seed_is_refused(tmp_path):
    client = _client_over(tmp_path)

    refused_count = _generate_with(client, count=MAXIMUM_DATASET_RECORDS + 1)
    refused_seed = _generate_with(client, seed=MAXIMUM_STORED_INTEGER + 1)

    assert refused_count.status_code == 422, refused_count.text
    assert "count" in refused_count.text, refused_count.text
    assert refused_seed.status_code == 422, refused_seed.text
    assert "seed" in refused_seed.text, refused_seed.text


def test_generating_in_an_unsupported_format_is_refused(tmp_path):
    client = _client_over(tmp_path)

    refused = _generate_with(client, format="parquet")

    assert refused.status_code == 422, refused.text
    assert "format" in refused.text, refused.text
