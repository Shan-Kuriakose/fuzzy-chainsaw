"""Acceptance tests for deterministic, seed-based repeatable generation.

Each test maps to an acceptance criterion of the story:
AC1 - the same seed and configuration produce byte-for-byte identical
      datasets, and omitting the seed is refused loudly
AC2 - a saved dataset replays to exactly the records it was built from
AC3 - the output records the seed and configuration the run used, and the
      configuration round-trips losslessly for replay
"""

import json

import pytest


def _seeded_dataset(count=10, seed=42, **config_overrides):
    from persona_engine import GenerationConfig, PersonaGenerator

    config = GenerationConfig(**config_overrides)
    return PersonaGenerator().generate_dataset(config, count=count, seed=seed)


def test_same_seed_and_config_yields_byte_identical_datasets():
    from persona_engine import serialization

    first = _seeded_dataset(count=25, seed=2026)
    second = _seeded_dataset(count=25, seed=2026)

    assert serialization.to_json_bytes(first) == serialization.to_json_bytes(second)


def test_dataset_generation_without_seed_raises():
    from persona_engine import GenerationConfig, PersonaGenerator

    generator = PersonaGenerator()

    with pytest.raises(TypeError):
        generator.generate_dataset(GenerationConfig(), count=10)


def test_replaying_saved_dataset_bytes_reproduces_the_failing_records():
    from persona_engine import serialization

    dataset = _seeded_dataset(count=30, seed=7, genders=("Female", "Male"))
    saved = serialization.to_json_bytes(dataset)

    decoded = serialization.manifest_from_bytes(saved)
    replayed = serialization.replay(decoded)

    assert replayed.personas == dataset.personas
    assert serialization.to_json_bytes(replayed) == saved


def test_dataset_round_trip_through_json_is_lossless():
    from persona_engine import serialization

    dataset = _seeded_dataset(count=15, seed=99, age_range=(40, 60))
    saved = serialization.to_json_bytes(dataset)

    replayed = serialization.replay(serialization.manifest_from_bytes(saved))
    assert len(replayed.personas) == len(dataset.personas)

    for original, restored in zip(dataset.personas, replayed.personas):
        assert (restored.first_name, restored.last_name) == (
            original.first_name,
            original.last_name,
        )
        assert restored.gender == original.gender
        assert restored.geography == original.geography
        assert restored.age == original.age and type(restored.age) is int
        assert restored.income == original.income and type(restored.income) is int


def test_json_output_embeds_seed_and_configuration():
    from persona_engine import serialization

    dataset = _seeded_dataset(
        count=12,
        seed=1234,
        age_range=(25, 45),
        geographies=("Region Alpha", "Region Beta"),
    )

    manifest = json.loads(serialization.to_json_bytes(dataset))

    assert manifest["seed"] == dataset.seed
    assert manifest["seed"] == 1234
    assert manifest["count"] == 12
    assert "manifest_version" in manifest
    assert "python_version" in manifest
    assert manifest["configuration"]["age_range"] == [25, 45]
    assert manifest["configuration"]["geographies"] == [
        "Region Alpha",
        "Region Beta",
    ]
    assert len(manifest["personas"]) == 12


def test_configuration_payload_round_trips():
    from persona_engine import GenerationConfig

    config = GenerationConfig(
        age_range=(30, 55),
        genders=("Non-Binary",),
        geographies=("Region Gamma",),
        income_range=(35_000, 90_000),
    )

    restored = GenerationConfig.from_payload(config.to_payload())

    assert restored == config
    assert restored.age_range == (30, 55)
    assert restored.age_range.__class__ is tuple
    assert restored.income_range == (35_000, 90_000)
    assert restored.income_range.__class__ is tuple
