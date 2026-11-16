"""Acceptance tests for batch generation at configurable scale.

Each test maps to an acceptance criterion of the story:
AC1 - a batch request with a record count produces exactly that many
      personas, and non-positive counts and batch sizes are refused
      before anything is generated
AC2 - a large batch streams progress as it goes and completes with every
      record, byte-identical to the single-shot generation it mirrors
AC3 - a batch's records are structurally uniform and the dataset replays
      through the saved manifest
"""

import pytest


def _batched_dataset(count, seed=42, **config_overrides):
    from persona_engine import GenerationConfig, generate_batch

    config = GenerationConfig(**config_overrides)
    return generate_batch(config, count, seed=seed)


def test_batch_yields_exactly_the_requested_number_of_personas():
    dataset = _batched_dataset(count=137)

    assert len(dataset.personas) == 137


def test_non_positive_count_is_refused():
    from persona_engine import GenerationConfig, generate_batch

    config = GenerationConfig()
    for count in (0, -5):
        with pytest.raises(ValueError) as refused:
            generate_batch(config, count, seed=42)
        assert str(count) in str(refused.value)


def test_non_positive_batch_size_is_refused():
    from persona_engine import GenerationConfig, generate_batch

    config = GenerationConfig()
    for batch_size in (0, -10):
        with pytest.raises(ValueError) as refused:
            generate_batch(config, 25, seed=42, batch_size=batch_size)
        assert str(batch_size) in str(refused.value)


def test_large_batch_streams_progress_and_completes_with_all_records():
    from persona_engine import GenerationConfig, generate_batch

    progress_events = []
    dataset = generate_batch(
        GenerationConfig(),
        count=1_250,
        seed=42,
        batch_size=400,
        on_progress=lambda completed, total: progress_events.append(
            (completed, total)
        ),
    )

    assert progress_events == [
        (400, 1_250),
        (800, 1_250),
        (1_200, 1_250),
        (1_250, 1_250),
    ]
    assert len(dataset.personas) == 1_250


def test_batch_output_matches_single_shot_generation_byte_for_byte():
    from persona_engine import (
        GenerationConfig,
        PersonaGenerator,
        generate_batch,
        serialization,
    )

    config = GenerationConfig()
    batched = generate_batch(config, 40, seed=2026, batch_size=7)
    single_shot = PersonaGenerator().generate_dataset(
        config, count=40, seed=2026
    )

    assert serialization.to_json_bytes(batched) == serialization.to_json_bytes(
        single_shot
    )


def test_batch_records_are_structurally_uniform():
    from persona_engine import name_pools

    dataset = _batched_dataset(
        count=60,
        seed=99,
        age_range=(30, 50),
        genders=("Female", "Male"),
        geographies=("Region Alpha",),
        income_range=(40_000, 90_000),
    )

    record_keys = {
        tuple(sorted(persona.to_payload())) for persona in dataset.personas
    }
    assert len(record_keys) == 1

    for persona in dataset.personas:
        assert persona.first_name in name_pools.FIRST_NAMES
        assert persona.last_name in name_pools.LAST_NAMES
        assert type(persona.age) is int and 30 <= persona.age <= 50
        assert persona.gender in ("Female", "Male")
        assert persona.geography == "Region Alpha"
        assert type(persona.income) is int and 40_000 <= persona.income <= 90_000


def test_batch_dataset_replays_through_the_saved_manifest():
    from persona_engine import serialization

    dataset = _batched_dataset(count=33, seed=7)
    saved = serialization.to_json_bytes(dataset)

    replayed = serialization.replay(serialization.manifest_from_bytes(saved))

    assert replayed.personas == dataset.personas
    assert serialization.to_json_bytes(replayed) == saved
