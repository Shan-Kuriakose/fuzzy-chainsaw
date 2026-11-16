"""Acceptance tests for configurable-scale batch dataset generation.

Each test maps to an acceptance criterion of the story:
AC1 - a batch request with a record count produces exactly that many
      personas, and invalid counts and batch sizes are refused before
      anything is generated
AC2 - a large batch completes without data loss while streaming progress
      to the caller, and is byte-identical to the single-shot dataset at
      any batch size
AC3 - batch output is structurally uniform record-to-record and replays
      through the saved manifest like any other dataset
"""

import pytest


def _config(**overrides):
    from persona_engine import GenerationConfig

    return GenerationConfig(**overrides)


def _generate_batch(config, count, *, seed, batch_size=None, on_progress=None):
    from persona_engine import batch

    if batch_size is None:
        return batch.generate_batch(config, count, seed=seed, on_progress=on_progress)
    return batch.generate_batch(
        config, count, seed=seed, batch_size=batch_size, on_progress=on_progress
    )


def test_batch_yields_exactly_the_requested_number_of_personas():
    from persona_engine import GeneratedDataset

    dataset = _generate_batch(_config(), 37, seed=5)

    assert isinstance(dataset, GeneratedDataset)
    assert len(dataset.personas) == 37


def test_non_positive_count_is_refused():
    offending_counts = (0, -7, 12.5)

    for offending_count in offending_counts:
        with pytest.raises(ValueError) as raised:
            _generate_batch(_config(), offending_count, seed=1)

        assert str(offending_count) in str(raised.value)


def test_non_positive_batch_size_is_refused():
    offending_batch_sizes = (0, -1000)

    for offending_batch_size in offending_batch_sizes:
        with pytest.raises(ValueError) as raised:
            _generate_batch(_config(), 10, seed=1, batch_size=offending_batch_size)

        assert str(offending_batch_size) in str(raised.value)


def test_large_batch_streams_progress_and_completes_with_all_records():
    from persona_engine import name_pools

    progress = []

    dataset = _generate_batch(
        _config(),
        50,
        seed=42,
        batch_size=10,
        on_progress=lambda completed, total: progress.append((completed, total)),
    )

    assert len(dataset.personas) == 50
    assert len(progress) > 1
    assert {total for _, total in progress} == {50}
    completed_values = [completed for completed, _ in progress]
    assert completed_values == sorted(completed_values)
    assert completed_values[-1] == 50
    for persona in dataset.personas:
        assert persona.first_name in name_pools.FIRST_NAMES
        assert persona.last_name in name_pools.LAST_NAMES


def test_batch_output_matches_single_shot_generation_byte_for_byte():
    from persona_engine import PersonaGenerator, serialization

    config = _config()

    for batch_size in (1, 7, 4096):
        batched = _generate_batch(config, 23, seed=1234, batch_size=batch_size)
        single_shot = PersonaGenerator().generate_dataset(config, count=23, seed=1234)

        assert serialization.to_json_bytes(batched) == serialization.to_json_bytes(
            single_shot
        )


def test_batch_records_are_structurally_uniform():
    from persona_engine import Persona

    config = _config(
        age_range=(30, 40),
        genders=("Female",),
        geographies=("Region Alpha",),
        income_range=(40_000, 50_000),
    )

    dataset = _generate_batch(config, 60, seed=3)

    assert len(dataset.personas) > 1
    for persona in dataset.personas:
        assert isinstance(persona, Persona)
        assert isinstance(persona.first_name, str) and persona.first_name
        assert isinstance(persona.last_name, str) and persona.last_name
        assert isinstance(persona.age, int) and 30 <= persona.age <= 40
        assert persona.gender == "Female"
        assert persona.geography == "Region Alpha"
        assert isinstance(persona.income, int) and 40_000 <= persona.income <= 50_000


def test_batch_dataset_replays_through_the_saved_manifest():
    from persona_engine import serialization

    dataset = _generate_batch(_config(), 40, seed=77, batch_size=15)
    saved = serialization.to_json_bytes(dataset)

    replayed = serialization.replay(serialization.manifest_from_bytes(saved))

    assert replayed.personas == dataset.personas
    assert serialization.to_json_bytes(replayed) == saved
