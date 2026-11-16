"""Acceptance tests for the dataset configuration and generation API.

AC1 - the defaults endpoint serves the built-in census-style distributions
AC2 - the generate endpoint returns a manifest reproducible from one seed
     (and refuses a malformed or oversized request along the way)
"""

_GENERATE_REQUEST = {"count": 5, "seed": 7}
_REFUSAL_STATUS_CODES = (400, 409, 422)
# 404 is deliberately absent: a missing feature produces 404, and a
# refusal must come from the configured batch rules instead.


def _client():
    from fastapi.testclient import TestClient

    from app.main import create_app

    return TestClient(create_app())


def _capped_client(max_dataset_rows):
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.settings import Settings

    settings = Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        max_dataset_rows=max_dataset_rows,
    )
    return TestClient(create_app(settings))


def test_defaults_endpoint_returns_the_built_in_census_style_distribution():
    from persona_engine import demographic_defaults

    response = _client().get("/api/datasets/defaults")

    assert response.status_code == 200
    payload = response.json()
    assert payload["distributions"] == demographic_defaults.DEFAULT_DISTRIBUTIONS
    assert payload["limits"]["max_count"] > 0


def test_generate_endpoint_returns_manifest_reproducible_from_same_seed():
    client = _client()

    first = client.post("/api/datasets/generate", json=_GENERATE_REQUEST)
    second = client.post("/api/datasets/generate", json=_GENERATE_REQUEST)

    assert first.status_code == 200
    manifest = first.json()
    assert manifest["seed"] == 7
    rows = manifest["personas"]
    assert len(rows) == manifest["count"] == 5
    assert set(rows[0]) == {
        "first_name",
        "last_name",
        "age",
        "gender",
        "geography",
        "income",
    }
    assert second.status_code == 200
    assert second.json()["personas"] == rows


def test_generate_refuses_a_zero_batch_with_a_client_error():
    response = _client().post(
        "/api/datasets/generate", json={"count": 0, "seed": 7}
    )

    assert response.status_code in _REFUSAL_STATUS_CODES


def test_generate_refuses_a_batch_over_the_configured_maximum():
    response = _capped_client(max_dataset_rows=10).post(
        "/api/datasets/generate", json={"count": 25, "seed": 7}
    )

    assert response.status_code in _REFUSAL_STATUS_CODES


def test_generate_refuses_a_request_without_a_count():
    response = _client().post("/api/datasets/generate", json={"seed": 7})

    assert response.status_code in _REFUSAL_STATUS_CODES
