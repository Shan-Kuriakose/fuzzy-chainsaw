"""Acceptance tests for the dataset-configuration validate endpoint (AC3).

Each test maps to an acceptance criterion of the story:
AC3 - given a configuration that would produce an unrealistic or invalid
      population, when it is submitted, then the app surfaces a warning
      before generation proceeds; an invalid configuration that the
      engine refuses is refused by the endpoint as loudly.
"""

VALIDATE_PATH = "/api/dataset-configurations/validate"

DEFAULT_FRAME = {
    "age_range": [18, 85],
    "genders": ["Female", "Male", "Non-Binary"],
    "geographies": [
        "Region North",
        "Region South",
        "Region East",
        "Region West",
    ],
    "income_range": [20_000, 150_000],
}


def _validated(config_payload):
    from fastapi.testclient import TestClient

    from app.main import create_app

    client = TestClient(create_app())
    return client.post(VALIDATE_PATH, json=config_payload)


def _config_payload(**overrides):
    payload = dict(DEFAULT_FRAME)
    payload.update(overrides)
    return payload


def test_invalid_configuration_is_refused_loudly():
    invalid_payload = _config_payload(
        genders=["Female", "Male", "Non-Binary"],
        distributions={"gender_weights": [0.8, 0.2]},
    )

    response = _validated(invalid_payload)

    assert response.status_code == 422


def test_unrealistic_configuration_surfaces_warnings():
    unrealistic_payload = _config_payload(
        genders=["Female", "Male"],
        distributions={"gender_weights": [0.95, 0.05]},
    )

    response = _validated(unrealistic_payload)

    assert response.status_code == 200
    assert response.json()["warnings"], "a 95% single-gender frame must warn"
    assert any("gender" in warning.lower() for warning in response.json()["warnings"])


def test_clean_configuration_reports_no_warnings():
    response = _validated(_config_payload())

    assert response.status_code == 200
    assert response.json()["warnings"] == []
