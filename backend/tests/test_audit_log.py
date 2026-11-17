"""Acceptance tests for the audit logging of dataset operations.

Each test maps to an acceptance criterion of the story:
AC3 - the UI path (save and reproduce) and the API path (generate and
      export) write the same audit records: one row per operation naming
      the action, team, subject, the seed, count and format where they
      apply, and an outcome that states succeeded or refused. A refused
      operation is audited as refused and never resembles a success.

The recorded rows are read back through the audit log's own adapter,
``SqlAlchemyAuditLog.recorded_events()``, over the same database the
application under test was pointed at; every row carries ``action``,
``team``, ``subject``, ``seed``, ``count``, ``format``, ``outcome`` and
``occurred_at``.
"""

ATLAS_TEAM = "atlas"

API_KEY = "atlas-pipeline-key"

SAVED_NAME = "atlas-audited-baseline"
SAVED_COUNT = 6
SAVED_SEED = 42
SAVED_CONFIGURATION = {
    "age_range": [25, 45],
    "genders": ["Female", "Male"],
    "geographies": ["Region North"],
    "income_range": [30_000, 90_000],
}

GENERATED_COUNT = 4
GENERATED_SEED = 11

FORBIDDEN_GENDER = "Unlisted Gender"

AUTHORIZATION_HEADER = {"Authorization": f"Bearer {API_KEY}"}


def _forbidden_values_file(tmp_path):
    path = tmp_path / "forbidden-values.txt"
    path.write_text(f"{FORBIDDEN_GENDER}\nForsaken Region\n", encoding="utf-8")
    return path


def _client_over(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.settings import Settings

    settings = Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        database_url=_database_url(tmp_path),
        api_key=API_KEY,
        forbidden_values_path=_forbidden_values_file(tmp_path),
    )
    return TestClient(create_app(settings=settings))


def _database_url(tmp_path):
    return f"sqlite:///{tmp_path / 'audit.db'}"


def _recorded_audit_events(tmp_path):
    from app.storage.audit_repository import SqlAlchemyAuditLog
    from app.storage.database import build_engine, build_session_factory

    audit_log = SqlAlchemyAuditLog(
        build_session_factory(build_engine(_database_url(tmp_path)))
    )
    return audit_log.recorded_events()


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


def test_saving_and_reproducing_from_the_ui_path_writes_audit_records(tmp_path):
    client = _client_over(tmp_path)
    save_response = _save_configuration(client)
    assert save_response.status_code == 201, save_response.text
    reproduce_response = client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations/{SAVED_NAME}/reproduce"
    )
    assert reproduce_response.status_code == 200, reproduce_response.text

    events = _recorded_audit_events(tmp_path)

    saved = [event for event in events if event.action == "dataset_saved"]
    reproduced = [
        event for event in events if event.action == "dataset_reproduced"
    ]
    assert len(saved) == 1, [str(event) for event in events]
    assert len(reproduced) == 1, [str(event) for event in events]
    assert saved[0].team == ATLAS_TEAM, saved[0]
    assert saved[0].subject == SAVED_NAME, saved[0]
    assert saved[0].seed == SAVED_SEED, saved[0]
    assert saved[0].count == SAVED_COUNT, saved[0]
    assert saved[0].outcome == "succeeded", saved[0]
    assert saved[0].occurred_at is not None, saved[0]
    assert reproduced[0].team == ATLAS_TEAM, reproduced[0]
    assert reproduced[0].subject == SAVED_NAME, reproduced[0]


def test_generating_from_the_api_path_writes_the_same_shaped_audit_row(tmp_path):
    client = _client_over(tmp_path)

    generated = client.post(
        f"/api/teams/{ATLAS_TEAM}/generated-datasets",
        json={
            "count": GENERATED_COUNT,
            "seed": GENERATED_SEED,
            "format": "csv",
            "configuration": SAVED_CONFIGURATION,
        },
        headers=AUTHORIZATION_HEADER,
    )
    assert generated.status_code == 200, generated.text

    events = _recorded_audit_events(tmp_path)

    generated_rows = [
        event for event in events if event.action == "dataset_generated"
    ]
    assert len(generated_rows) == 1, [str(event) for event in events]
    row = generated_rows[0]
    assert row.team == ATLAS_TEAM, row
    assert row.seed == GENERATED_SEED, row
    assert row.count == GENERATED_COUNT, row
    assert row.format == "csv", row
    assert row.outcome == "succeeded", row
    assert row.occurred_at is not None, row


def test_exporting_from_the_api_path_writes_an_audit_row(tmp_path):
    client = _client_over(tmp_path)
    save_response = _save_configuration(client)
    assert save_response.status_code == 201, save_response.text

    exported = client.get(
        f"/api/teams/{ATLAS_TEAM}/dataset-configurations/{SAVED_NAME}/export",
        params={"format": "json"},
        headers=AUTHORIZATION_HEADER,
    )
    assert exported.status_code == 200, exported.text

    events = _recorded_audit_events(tmp_path)

    exported_rows = [
        event for event in events if event.action == "dataset_exported"
    ]
    assert len(exported_rows) == 1, [str(event) for event in events]
    row = exported_rows[0]
    assert row.team == ATLAS_TEAM, row
    assert row.subject == SAVED_NAME, row
    assert row.format == "json", row
    assert row.outcome == "succeeded", row


def test_a_refused_generation_is_audited_as_refused(tmp_path):
    client = _client_over(tmp_path)

    refused = client.post(
        f"/api/teams/{ATLAS_TEAM}/generated-datasets",
        json={
            "count": GENERATED_COUNT,
            "seed": GENERATED_SEED,
            "format": "csv",
            "configuration": {
                **SAVED_CONFIGURATION,
                "genders": ["Female", FORBIDDEN_GENDER],
            },
        },
        headers=AUTHORIZATION_HEADER,
    )
    assert refused.status_code == 422, refused.text

    events = _recorded_audit_events(tmp_path)

    generated_rows = [
        event for event in events if event.action == "dataset_generated"
    ]
    assert len(generated_rows) == 1, [str(event) for event in events]
    row = generated_rows[0]
    assert row.outcome == "refused", row
    assert row.team == ATLAS_TEAM, row
