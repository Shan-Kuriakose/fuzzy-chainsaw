"""Acceptance tests for exporting generated datasets in CSV and JSON.

Each test maps to an acceptance criterion of the story:
AC1 - a requested export produces a CSV or JSON file carrying every
      record and attribute of the generated dataset
AC2 - an exported file loads into a downstream tool without schema
      errors, verified through the format's reference reader
      (csv.DictReader / json.loads) with a consistent schema
AC3 - an export is free of real member identities: de-identification
      by construction, every exported value drawn only from the
      committed name pools or the configured ranges
"""

import csv
import json
from dataclasses import fields
from io import StringIO


def _seeded_dataset(count, **config_overrides):
    from persona_engine import GenerationConfig, PersonaGenerator

    config = GenerationConfig(**config_overrides)
    return PersonaGenerator().generate_dataset(config, count=count, seed=123)


def _csv_rows(export_bytes):
    return list(csv.DictReader(StringIO(export_bytes.decode("utf-8"))))


def test_csv_export_contains_every_record_and_attribute():
    from persona_engine.serialization import to_csv_bytes

    dataset = _seeded_dataset(7, genders=("Female", "Non-Binary"))

    rows = _csv_rows(to_csv_bytes(dataset))

    expected_rows = [
        {key: str(value) for key, value in persona.to_payload().items()}
        for persona in dataset.personas
    ]
    assert rows == expected_rows


def test_json_records_export_contains_every_record_and_attribute():
    from persona_engine.serialization import to_json_records_bytes

    dataset = _seeded_dataset(9, age_range=(40, 60))

    records = json.loads(to_json_records_bytes(dataset).decode("utf-8"))

    expected_records = [persona.to_payload() for persona in dataset.personas]
    assert records == expected_records
    assert all(type(record["age"]) is int for record in records)
    assert all(type(record["income"]) is int for record in records)


def test_csv_export_round_trips_through_the_reference_reader_with_a_consistent_schema():
    from persona_engine.persona import Persona
    from persona_engine.serialization import to_csv_bytes

    dataset = _seeded_dataset(7)
    single_record = _seeded_dataset(1)
    empty = _seeded_dataset(0)

    expected_header = [field.name for field in fields(Persona)]

    parsed = _csv_rows(to_csv_bytes(dataset))
    assert list(parsed[0]) == expected_header
    for row in parsed + _csv_rows(to_csv_bytes(single_record)):
        assert set(row) == set(expected_header)

    reader = csv.DictReader(StringIO(to_csv_bytes(empty).decode("utf-8")))
    assert reader.fieldnames == expected_header
    assert list(reader) == []


def test_json_records_export_parses_as_typed_records_without_schema_errors():
    from persona_engine.persona import Persona
    from persona_engine.serialization import to_json_records_bytes

    dataset = _seeded_dataset(7)
    empty = _seeded_dataset(0)

    records = json.loads(to_json_records_bytes(dataset).decode("utf-8"))
    expected_field_names = {field.name for field in fields(Persona)}

    assert all(set(record) == expected_field_names for record in records)
    assert all(type(record["age"]) is int for record in records)
    assert all(type(record["income"]) is int for record in records)
    assert json.loads(to_json_records_bytes(empty).decode("utf-8")) == []


def test_exported_values_come_only_from_committed_pools_and_configured_ranges():
    from persona_engine import name_pools
    from persona_engine.serialization import to_csv_bytes, to_json_records_bytes

    dataset = _seeded_dataset(
        40,
        age_range=(19, 62),
        genders=("Female", "Male"),
        geographies=("Region Alpha", "Region Beta"),
        income_range=(30_000, 70_000),
    )
    age_low, age_high = dataset.configuration.age_range
    income_low, income_high = dataset.configuration.income_range

    exports = [
        json.loads(to_json_records_bytes(dataset).decode("utf-8")),
        _csv_rows(to_csv_bytes(dataset)),
    ]
    for records in exports:
        assert len(records) == 40
        for record in records:
            assert record["first_name"] in name_pools.FIRST_NAMES
            assert record["last_name"] in name_pools.LAST_NAMES
            assert age_low <= int(record["age"]) <= age_high
            assert income_low <= int(record["income"]) <= income_high
            assert record["gender"] in dataset.configuration.genders
            assert record["geography"] in dataset.configuration.geographies
