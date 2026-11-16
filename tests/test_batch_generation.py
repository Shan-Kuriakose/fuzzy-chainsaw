"""Acceptance tests for generating batch datasets at configurable scale.

Each test maps to an acceptance criterion of the story:
AC1 - a batch request with a record count produces exactly that number of
      personas, and non-positive or non-integer requests are refused loudly
AC2 - a large batch completes with every record and reports progress as
      it streams through
AC3 - batch output is structurally consistent record-to-record and ready
      for schema validation, and replays through the saved manifest
"""

import pytest


def _batched_dataset(count, *, seed, batch_size, on_progress=None, **config_overrides):
    from persona_engine import GenerationConfig
    from persona_engine.batch import generate_batch

    config = GenerationConfig(**config_overrides)
    return generate_batch(
        config, count, seed=seed, batch_size=batch_size, on_progress=on_progress
    )


def test_batch_yields_exactly_the_requested_number_of_personas():
    dataset = _batched_dataset(137, seed=42, batch_size=40)

    assert len(dataset.personas) == 137


def test_zero_count_is_refused():
    from persona_engine import GenerationConfig
    from persona_engine.batch import generate_batch

    with pytest.raises(ValueError, match="0"):
        generate_batch(GenerationConfig(), count=0, seed=42)


def test_negative_count_is_refused():
    from persona_engine import GenerationConfig
    from persona_engine.batch import generate_batch

    with pytest.raises(ValueError, match="-7"):
        generate_batch(GenerationConfig(), count=-7, seed=42)


def test_non_integer_count_is_refused():
    from persona_engine import GenerationConfig
    from persona_engine.batch import generate_batch

    with pytest.raises(ValueError, match="1.5"):
        generate_batch(GenerationConfig(), count=1.5, seed=42)


def test_non_positive_batch_size_is_refused():
    from persona_engine import GenerationConfig
    from persona_engine.batch import generate_batch

    with pytest.raises(ValueError, match="0"):
        generate_batch(GenerationConfig(), count=10, seed=42, batch_size=0)


def test_large_batch_streams_progress_and_completes_with_all_records():
    total_records = 5_500

    progress = []
    dataset = _batched_dataset(
        total_records,
        seed=8,
        batch_size=1_000,
        on_progress=lambda completed, total: progress.append((completed, total)),
    )

    assert len(dataset.personas) == total_records
    assert [completed for completed, _ in progress] == [
        1_000, 2_000, 3_000, 4_000, 5_000, 5_500,
    ]
    assert progress == [
        (completed, total_records) for completed, _ in progress
    ]
    assert progress[-1] == (total_records, total_records)


def test_batch_output_matches_single_shot_generation_byte_for_byte():
    from persona_engine import GenerationConfig, PersonaGenerator
    from persona_engine import serialization

    config = GenerationConfig(age_range=(20, 70))
    single_shot = PersonaGenerator().generate_dataset(config, count=157, seed=11)

    ragged_chunks = _batched_dataset(157, seed=11, batch_size=50)
    one_chunk = _batched_dataset(157, seed=11, batch_size=157)

    assert serialization.to_json_bytes(ragged_chunks) == serialization.to_json_bytes(
        single_shot
    )
    assert serialization.to_json_bytes(one_chunk) == serialization.to_json_bytes(
        single_shot
    )


def test_batch_records_are_structurally_uniform():
    dataset = _batched_dataset(
        120,
        seed=3,
        batch_size=47,
        age_range=(30, 65),
        income_range=(25_000, 90_000),
        genders=("Non-Binary",),
        geographies=("Region Alpha",),
    )

    payloads = [persona.to_payload() for persona in dataset.personas]
    assert all(payload.keys() == payloads[0].keys() for payload in payloads)

    for payload in payloads:
        assert type(payload["age"]) is int and 30 <= payload["age"] <= 65
        assert type(payload["income"]) is int and 25_000 <= payload["income"] <= 90_000
        assert type(payload["first_name"]) is str and payload["first_name"]
        assert type(payload["last_name"]) is str and payload["last_name"]
        assert type(payload["gender"]) is str and payload["gender"] == "Non-Binary"
        assert type(payload["geography"]) is str and payload["geography"] == "Region Alpha"


def test_batch_dataset_replays_through_the_saved_manifest():
    from persona_engine import serialization

    dataset = _batched_dataset(85, seed=77, batch_size=20)
    saved = serialization.to_json_bytes(dataset)

    decoded = serialization.manifest_from_bytes(saved)
    replayed = serialization.replay(decoded)

    assert replayed.personas == dataset.personas
    assert serialization.to_json_bytes(replayed) == saved
