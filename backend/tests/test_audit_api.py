"""API acceptance test for querying the audit history over HTTP.

AC3 through the API: the query endpoint lists the audit records that
match the requested user, each carrying the actor, the moment, the
action and the configuration reference a reviewer needs.
"""

from datetime import datetime

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

JANE_DOE = "jane.doe@example.com"
JOHN_SMITH = "john.smith@example.com"

AUDIT_RECORDS_ROUTE = "/api/audit-records"
ACTING_USER_HEADER = "X-Acting-User"


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


def _save_by_jane_and_reuse_by_john(client):
    save_response = client.put(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations",
        headers={ACTING_USER_HEADER: JANE_DOE},
        json={
            "name": SAVED_NAME,
            "count": SAVED_COUNT,
            "seed": SAVED_SEED,
            "configuration": SAVED_CONFIGURATION,
        },
    )
    assert save_response.status_code == 201, save_response.text

    reuse_response = client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations/{SAVED_NAME}/reproduce",
        headers={ACTING_USER_HEADER: JOHN_SMITH},
    )
    assert reuse_response.status_code == 200, reuse_response.text


def test_history_is_served_by_the_audit_api(tmp_path):
    from app.audit.trail import (
        DATASET_CONFIGURATION_SAVED,
        DATASET_GENERATED,
        DATASET_REPRODUCED,
    )

    client = _client_over(tmp_path)
    _save_by_jane_and_reuse_by_john(client)

    matching = client.get(AUDIT_RECORDS_ROUTE, params={"user": JANE_DOE})

    assert matching.status_code == 200, matching.text
    saved_and_generated = matching.json()
    assert len(saved_and_generated) == 2
    for entry in saved_and_generated:
        assert entry["actor"] == JANE_DOE
        assert entry["team"] == ATLAS_TEAM
        assert entry["name"] == SAVED_NAME
        assert entry["action"] in (DATASET_GENERATED, DATASET_CONFIGURATION_SAVED)
        datetime.fromisoformat(entry["moment"])

    reused = client.get(AUDIT_RECORDS_ROUTE, params={"user": JOHN_SMITH})

    assert reused.status_code == 200, reused.text
    assert [(entry["actor"], entry["action"]) for entry in reused.json()] == [
        (JOHN_SMITH, DATASET_REPRODUCED)
    ]
