"""Service-level tests for saving and reproducing dataset configurations.

These name the refusals the service layer must raise before any
context-specific storage adapter is consulted: a duplicate name within a
team, an unsaved configuration, and a stored manifest that no longer
replays to its own rows.

They also pin the identity-safety screening that sits between generation
and persistence: every saved batch is screened against the supplied
non-PHI forbidden-value list, a withheld batch is never stored, and the
verdict of each screen is retrievable as pass/fail evidence.
"""

import hashlib
import json

import pytest

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

FORBIDDEN_GEOGRAPHY = "Region North"


def _configuration_with_geographies(geography):
    return {**SAVED_CONFIGURATION, "geographies": [geography]}


def _write_forbidden_values_file(tmp_path, forbidden_values):
    path = tmp_path / "forbidden-values.json"
    path.write_text(json.dumps(list(forbidden_values)), encoding="utf-8")
    return path


def _service_over(tmp_path, forbidden_values=()):
    from app.dataset_configurations.service import DatasetConfigurationsService
    from app.settings import Settings

    settings = Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'configurations.db'}",
        forbidden_values_path=str(
            _write_forbidden_values_file(tmp_path, forbidden_values)
        ),
    )
    return DatasetConfigurationsService.build_for(settings)


def _engine_rows_for_saved_configuration():
    from persona_engine import GenerationConfig, PersonaGenerator

    dataset = PersonaGenerator().generate_dataset(
        GenerationConfig.from_payload(SAVED_CONFIGURATION),
        count=SAVED_COUNT,
        seed=SAVED_SEED,
    )
    return [persona.to_payload() for persona in dataset.personas]


def _tamper_saved_manifest_rows(tmp_path):
    import sqlite3

    from persona_engine import serialization

    manifest = json.loads(serialization.to_json_bytes(_dataset()))
    manifest["personas"][0]["first_name"] = "Tampered"
    tampered = json.dumps(
        manifest, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")

    connection = sqlite3.connect(str(tmp_path / "configurations.db"))
    try:
        connection.execute(
            "UPDATE dataset_configurations SET manifest = ? WHERE name = ?",
            (sqlite3.Binary(tampered), SAVED_NAME),
        )
        connection.commit()
    finally:
        connection.close()


def _dataset():
    from persona_engine import GenerationConfig, PersonaGenerator

    return PersonaGenerator().generate_dataset(
        GenerationConfig.from_payload(SAVED_CONFIGURATION),
        count=SAVED_COUNT,
        seed=SAVED_SEED,
    )


def test_a_service_reproduces_a_dataset_from_its_saved_configuration(tmp_path):
    service = _service_over(tmp_path)

    service.save(ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED)

    reproduction = service.reproduce(ATLAS_TEAM, SAVED_NAME)

    assert reproduction["seed"] == SAVED_SEED
    assert reproduction["count"] == SAVED_COUNT
    assert reproduction["personas"] == _engine_rows_for_saved_configuration()


def test_a_service_refuses_a_second_save_of_a_name_within_a_team(tmp_path):
    service = _service_over(tmp_path)
    service.save(ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED)

    with pytest.raises(ValueError):
        service.save(ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, 6, SAVED_SEED + 1)


def test_a_service_refuses_reproducing_a_configuration_no_one_saved(tmp_path):
    service = _service_over(tmp_path)

    with pytest.raises(LookupError):
        service.reproduce(ATLAS_TEAM, SAVED_NAME)


def test_a_service_refuses_a_saved_manifest_that_no_longer_replays_to_its_own_rows(
    tmp_path,
):
    service = _service_over(tmp_path)
    service.save(ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED)
    _tamper_saved_manifest_rows(tmp_path)

    with pytest.raises(ValueError, match="not the saved ones"):
        service.reproduce(ATLAS_TEAM, SAVED_NAME)


def test_save_screens_generated_batch_and_records_verdict(tmp_path):
    service = _service_over(tmp_path, forbidden_values=["FORBIDDEN VALUE"])

    service.save(ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED)

    screenings = service.screenings_in_team(ATLAS_TEAM)
    assert [entry["name"] for entry in screenings] == [SAVED_NAME]
    assert [entry["passed"] for entry in screenings] == [True]


def test_save_records_fingerprint_of_the_list_that_approved_the_batch(tmp_path):
    service = _service_over(tmp_path, forbidden_values=["FORBIDDEN VALUE"])
    expected_fingerprint = hashlib.sha256(
        (tmp_path / "forbidden-values.json").read_bytes()
    ).hexdigest()

    service.save(ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED)

    screenings = service.screenings_in_team(ATLAS_TEAM)
    assert [entry["forbidden_values_sha256"] for entry in screenings] == [
        expected_fingerprint
    ]


def test_save_refuses_batch_containing_forbidden_value_and_stores_nothing(tmp_path):
    from app.dataset_configurations.service import WithheldDatasetConfiguration

    service = _service_over(tmp_path, forbidden_values=[FORBIDDEN_GEOGRAPHY])

    with pytest.raises(WithheldDatasetConfiguration):
        service.save(
            ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED
        )

    assert service.list_in_team(ATLAS_TEAM) == []


def test_refused_batch_is_flagged_with_failed_screening_record(tmp_path):
    from app.dataset_configurations.service import WithheldDatasetConfiguration

    service = _service_over(tmp_path, forbidden_values=[FORBIDDEN_GEOGRAPHY])

    with pytest.raises(WithheldDatasetConfiguration):
        service.save(
            ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED
        )

    screenings = service.screenings_in_team(ATLAS_TEAM)
    assert [entry["passed"] for entry in screenings] == [False]
    assert [entry["matched_values"] for entry in screenings] == [[FORBIDDEN_GEOGRAPHY]]


def test_reproduce_refuses_a_refused_batch(tmp_path):
    from app.dataset_configurations.service import WithheldDatasetConfiguration

    service = _service_over(tmp_path, forbidden_values=[FORBIDDEN_GEOGRAPHY])

    with pytest.raises(WithheldDatasetConfiguration):
        service.save(
            ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED
        )

    with pytest.raises(LookupError):
        service.reproduce(ATLAS_TEAM, SAVED_NAME)


def test_screenings_in_team_returns_pass_and_fail_evidence(tmp_path):
    from app.dataset_configurations.service import WithheldDatasetConfiguration

    service = _service_over(tmp_path, forbidden_values=[FORBIDDEN_GEOGRAPHY])
    service.save(
        ATLAS_TEAM,
        SAVED_NAME,
        _configuration_with_geographies("Region South"),
        SAVED_COUNT,
        SAVED_SEED,
    )

    with pytest.raises(WithheldDatasetConfiguration):
        service.save(
            ATLAS_TEAM,
            "atlas-withheld",
            SAVED_CONFIGURATION,
            SAVED_COUNT,
            SAVED_SEED,
        )

    screenings = service.screenings_in_team(ATLAS_TEAM)
    verdicts = {entry["name"]: entry["passed"] for entry in screenings}
    assert verdicts == {SAVED_NAME: True, "atlas-withheld": False}
