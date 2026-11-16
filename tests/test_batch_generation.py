"""Acceptance tests for scaling dataset generation to a requested size.

Each test maps to an acceptance criterion of the story:
AC1 - a batch with a record count produces exactly that many personas,
      and non-positive counts or batch sizes are refused loudly
AC2 - a large batch completes without data loss, streaming progress as
      chunks finish, and is identical to single-shot generation so the
      existing reproducibility boundary is untouched
AC3 - batch output is structurally consistent record to record and
      replays through the saved manifest like any other dataset
"""

import pytest


def _generate_batch(config, count, seed=42, **kwargs):
    from persona_engine import GenerationConfig
    from persona_engine.batch import generate_batch

    if config is None:
        config = GenerationConfig()
    return generate_batch(config, count, seed=seed, **kwargs)


def _recorded_progress():
    completed_counts, total_sizes = [], []

    def on_progress(completed, total):
        completed_counts.append(completed)
        total_sizes.append(total)

    return completed_counts, total_sizes, on_progress


def test_batch_yields_exactly_the_requested_number_of_personas():
    from persona_engine import GeneratedDataset

    dataset = _generate_batch(None, count=137)

    assert isinstance(dataset, GeneratedDataset)
    assert len(dataset.personas) == 137


def test_non_positive_count_is_refused():
    for refused_count in (0, -3):
        with pytest.raises(ValueError) as raised:
            _generate_batch(None, count=refused_count)

        assert str(refused_count) in str(raised.value)


def test_non_positive_batch_size_is_refused():
    for refused_size in (0, -10):
        with pytest.raises(ValueError) as raised:
            _generate_batch(None, count=50, batch_size=refused_size)

        assert str(refused_size) in str(raised.value)


def test_large_batch_streams_progress_and_completes_with_all_records():
    completed_counts, total_sizes, on_progress = _recorded_progress()

    dataset = _generate_batch(
        None, count=2_000, seed=7, on_progress=on_progress
    )

    assert total_sizes and set(total_sizes) == {2_000}
    assert completed_counts == sorted(completed_counts)
    assert completed_counts[-1] == 2_000
    assert len(dataset.personas) == 2_000


def test_batch_output_matches_single_shot_generation_byte_for_byte():
    from persona_engine import GenerationConfig, PersonaGenerator, serialization

    config = GenerationConfig(
        age_range=(30, 60),
        genders=("Female", "Male"),
        geographies=("Region Alpha", "Region Beta"),
        income_range=(40_000, 80_000),
    )
    batched = _generate_batch(
        config, count=120, seed=2026, batch_size=47
    )
    single_shot = PersonaGenerator().generate_dataset(
        config, count=120, seed=2026
    )

    assert serialization.to_json_bytes(batched) == serialization.to_json_bytes(
        single_shot
    )


def test_batch_records_are_structurally_uniform():
    from persona_engine import GenerationConfig

    config = GenerationConfig(
        age_range=(25, 55),
        genders=("Non-Binary", "Female"),
        geographies=("Region Gamma",),
        income_range=(30_000, 60_000),
    )
    dataset = _generate_batch(config, count=60, seed=5)

    expected_keys = set(dataset.personas[0].to_payload())
    for persona in dataset.personas:
        payload = persona.to_payload()
        assert set(payload) == expected_keys
        assert isinstance(persona.age, int)
        assert isinstance(persona.income, int)
        assert config.age_range[0] <= persona.age <= config.age_range[1]
        assert (
            config.income_range[0]
            <= persona.income
            <= config.income_range[1]
        )
        assert persona.gender in config.genders
        assert persona.geography in config.geographies
        assert all(isinstance(value, str) for value in
                   (persona.first_name, persona.last_name,
                    persona.gender, persona.geography))


def test_batch_dataset_replays_through_the_saved_manifest():
    from persona_engine import serialization

    dataset = _generate_batch(None, count=45, seed=88, batch_size=13)
    saved = serialization.to_json_bytes(dataset)

    replayed = serialization.replay(serialization.manifest_from_bytes(saved))

    assert replayed.personas == dataset.personas
    assert serialization.to_json_bytes(replayed) == saved
