"""API refusal tests for the audit history endpoint.

AC2 through the API: the audit history is served read-only - the query
route is there, but no mutation route exists, so an application user
cannot modify or delete an audit record over HTTP.
"""

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

AUDIT_RECORDS_ROUTE = "/api/audit-records"


def _client_with_an_audited_save(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.settings import Settings

    settings = Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'dataset-configurations.db'}",
    )
    client = TestClient(create_app(settings=settings))
    save_response = client.put(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations",
        json={
            "name": SAVED_NAME,
            "count": SAVED_COUNT,
            "seed": SAVED_SEED,
            "configuration": SAVED_CONFIGURATION,
        },
    )
    assert save_response.status_code == 201, save_response.text
    return client


def _forged_record():
    return {
        "actor": "whoever",
        "moment": "2026-11-16T10:00:00+00:00",
        "action": "dataset_generated",
        "team": ATLAS_TEAM,
        "name": SAVED_NAME,
    }


def test_a_mutation_request_to_the_audit_api_is_refused(tmp_path):
    client = _client_with_an_audited_save(tmp_path)

    served = client.get(AUDIT_RECORDS_ROUTE)
    assert served.status_code == 200, served.text

    for method in ("post", "put", "patch", "delete"):
        response = client.request(method, AUDIT_RECORDS_ROUTE, json=_forged_record())
        assert response.status_code in (404, 405), (
            method,
            response.status_code,
            response.text,
        )

    still_served = client.get(AUDIT_RECORDS_ROUTE)
    assert still_served.status_code == 200, still_served.text
