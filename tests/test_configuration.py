"""Configuration immutability tests.

A GenerationConfig is recorded inside a dataset as the provenance of a
run, so it must be frozen and hold only values no caller can reach back
into: assignment is refused, and list arguments are held as tuples.
"""

import dataclasses

import pytest


def _build_config(**overrides):
    from persona_engine import GenerationConfig

    return GenerationConfig(**overrides)


def test_config_attribute_assignment_is_refused():
    config = _build_config()

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.age_range = (99, 100)


def test_config_holds_list_arguments_as_tuples():
    config = _build_config(genders=["Female", "Male"])

    assert config.genders == ("Female", "Male")
    assert isinstance(config.genders, tuple)


def test_mutating_a_list_argument_does_not_touch_the_config():
    genders = ["Female", "Male"]
    config = _build_config(genders=genders)

    genders.append("Intruder")

    assert config.genders == ("Female", "Male")


def test_recorded_configuration_survives_caller_mutation():
    from persona_engine import PersonaGenerator, serialization

    geographies = ["Region Alpha", "Region Beta"]
    config = _build_config(geographies=geographies)
    dataset = PersonaGenerator().generate_dataset(config, count=5, seed=3)

    geographies.append("Region Intruder")

    manifest = serialization.to_json_bytes(dataset)
    recorded = manifest.decode("utf-8")
    assert "Region Intruder" not in recorded
    assert "Region Alpha" in recorded and "Region Beta" in recorded
