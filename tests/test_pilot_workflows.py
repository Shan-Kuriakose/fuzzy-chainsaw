"""Executable walkthroughs of the cross-persona pilot.

Each persona runs its primary workflow on the real surfaces the pilot
observes -- the persona engine, the dataset-configurations backend and
the committed privacy packet -- with no engine mocks. The walkthrough
then requires the pilot record to carry that persona's outcome with
evidence, so the record cannot claim a walkthrough that does not run.

Each test maps to the story's acceptance criteria:
AC1 - every persona's primary workflow completes, and its outcome is
      recorded in the pilot record
AC3 - the privacy persona's output review stands on the packet's
      recorded sign-off of the generation approach
"""

import csv
import io
import json
import sys

from conftest import REPO_ROOT, frontmatter_of, frontmatter_value, recorded_walkthrough

PRIVACY_PACKET_PATH = REPO_ROOT / "docs" / "privacy" / "generation-approach.md"

ANALYST_TEAM = "pilot-analysts"
ANALYST_CONFIGURATION_NAME = "pilot-baseline"
ANALYST_CONFIGURATION = {
    "age_range": [25, 45],
    "genders": ["Female", "Male"],
    "geographies": ["Region North"],
    "income_range": [30_000, 90_000],
}
ANALYST_COUNT = 10
ANALYST_SEED = 909

PERSONA_FIELD_NAMES = {
    "first_name",
    "last_name",
    "age",
    "gender",
    "geography",
    "income",
}


def _privacy_packet_text() -> str:
    if not PRIVACY_PACKET_PATH.exists():
        raise AssertionError(
            "the privacy packet must exist at "
            "docs/privacy/generation-approach.md"
        )
    return PRIVACY_PACKET_PATH.read_text(encoding="utf-8")


def _web_client_for_pilot(tmp_path):
    """Build the real FastAPI application over a temporary store."""

    backend_root = str(REPO_ROOT / "backend")
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.settings import Settings

    settings = Settings(
        app_name="cross-persona-pilot",
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'pilot-dataset-configurations.db'}",
    )
    return TestClient(create_app(settings=settings))


def _analyst_save_payload():
    return {
        "name": ANALYST_CONFIGURATION_NAME,
        "count": ANALYST_COUNT,
        "seed": ANALYST_SEED,
        "configuration": ANALYST_CONFIGURATION,
    }


def test_developer_primary_workflow_completes():
    from persona_engine import GenerationConfig, PersonaGenerator

    authored = GenerationConfig(
        age_range=(25, 45),
        genders=("Female", "Male"),
        geographies=("Region North", "Region South"),
        income_range=(30_000, 90_000),
    )
    dataset = PersonaGenerator().generate_dataset(authored, count=12, seed=101)

    assert dataset.seed == 101
    assert len(dataset.personas) == 12
    assert dataset.configuration == authored

    recorded_walkthrough("developer")


def test_qa_replay_workflow_completes():
    from persona_engine import GenerationConfig, PersonaGenerator, serialization

    dataset = PersonaGenerator().generate_dataset(
        GenerationConfig(), count=15, seed=77
    )
    saved = serialization.to_json_bytes(dataset)

    decoded = serialization.manifest_from_bytes(saved)
    replayed = serialization.replay(decoded)

    assert replayed.personas == dataset.personas
    assert serialization.to_json_bytes(replayed) == saved

    recorded_walkthrough("qa")


def test_bi_export_workflow_completes():
    from persona_engine import GenerationConfig, PersonaGenerator, serialization

    dataset = PersonaGenerator().generate_dataset(
        GenerationConfig(), count=8, seed=5
    )

    csv_rows = list(
        csv.reader(io.StringIO(serialization.to_csv_bytes(dataset).decode("utf-8")))
    )
    assert set(csv_rows[0]) == PERSONA_FIELD_NAMES, (
        "the CSV export must carry the persona schema in its header"
    )
    assert len(csv_rows) == len(dataset.personas) + 1, (
        "the CSV export must carry exactly one row per persona"
    )

    records = json.loads(
        serialization.to_json_records_bytes(dataset).decode("utf-8")
    )
    assert records == [persona.to_payload() for persona in dataset.personas]

    recorded_walkthrough("bi")


def test_analyst_web_workflow_completes(tmp_path):
    from persona_engine import GenerationConfig, PersonaGenerator

    client = _web_client_for_pilot(tmp_path)
    configurations_url = f"/api/teams/{ANALYST_TEAM}/dataset-configurations"

    saved = client.put(
        configurations_url, json=_analyst_save_payload()
    )
    assert saved.status_code == 201, saved.text

    listed = client.get(configurations_url)
    assert listed.status_code == 200, listed.text
    assert [entry["name"] for entry in listed.json()] == [
        ANALYST_CONFIGURATION_NAME
    ], listed.text
    assert listed.json()[0]["configuration"] == ANALYST_CONFIGURATION

    reproduced = client.get(
        f"{configurations_url}/{ANALYST_CONFIGURATION_NAME}/reproduce"
    )
    assert reproduced.status_code == 200, reproduced.text
    reproduction = reproduced.json()
    assert reproduction["seed"] == ANALYST_SEED
    assert reproduction["count"] == ANALYST_COUNT

    direct = PersonaGenerator().generate_dataset(
        GenerationConfig(**ANALYST_CONFIGURATION),
        count=ANALYST_COUNT,
        seed=ANALYST_SEED,
    )
    assert reproduction["personas"] == [
        persona.to_payload() for persona in direct.personas
    ]

    recorded_walkthrough("analyst")


def test_privacy_output_review_completes():
    from conftest import markdown_tables, table_with_columns

    from persona_engine import GenerationConfig, PersonaGenerator
    from persona_engine.name_pools import FIRST_NAMES, LAST_NAMES

    config = GenerationConfig()
    dataset = PersonaGenerator().generate_dataset(config, count=50, seed=2026)

    for persona in dataset.personas:
        assert persona.first_name in FIRST_NAMES, (
            f"'{persona.first_name}' is not a committed synthetic first name"
        )
        assert persona.last_name in LAST_NAMES, (
            f"'{persona.last_name}' is not a committed synthetic last name"
        )
        assert config.age_range[0] <= persona.age <= config.age_range[1]
        assert persona.gender in config.genders
        assert persona.geography in config.geographies
        assert config.income_range[0] <= persona.income <= config.income_range[1]

    packet = _privacy_packet_text()
    status = frontmatter_value(frontmatter_of(packet), "status").lower()
    assert "pending" not in status, (
        "the privacy packet's status must no longer defer the sign-off; "
        f"the pilot reviews the signed-off approach, found: '{status}'"
    )

    approval_header, approval_rows = table_with_columns(
        packet, "decision", "rationale", "date"
    )
    signed_off = [
        row
        for row in approval_rows
        if "pending" not in row[approval_header.index("decision")]
        and row[approval_header.index("rationale")] not in
        ("", "recorded at sign-off")
        and row[approval_header.index("date")] not in ("", "—", "-")
    ]
    assert signed_off, (
        "the privacy packet's approval record must carry a signed-off "
        "decision with a recorded rationale and date"
    )

    recorded_walkthrough("privacy")
