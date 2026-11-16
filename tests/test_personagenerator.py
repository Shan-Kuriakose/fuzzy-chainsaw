"""Acceptance tests for the synthetic persona generation engine.

Each test maps to an acceptance criterion of the story:
AC1 - a generated persona carries name and demographic attributes
AC2 - unseeded generation varies; seeded generation is reproducible
AC3 - every attribute stays inside the configured, synthetic ranges
"""

import random

import pytest


def _default_config(**overrides):
    from persona_engine import GenerationConfig

    return GenerationConfig(**overrides)


def _generate(config=None):
    from persona_engine import PersonaGenerator

    generator = PersonaGenerator()
    return generator.generate(config if config is not None else _default_config())


def test_generate_returns_persona_with_all_attributes():
    from persona_engine import Persona

    persona = _generate()

    assert isinstance(persona, Persona)
    assert persona.first_name
    assert persona.last_name
    assert isinstance(persona.age, int)
    assert persona.age > 0
    assert persona.gender
    assert persona.geography
    assert isinstance(persona.income, (int, float))
    assert persona.income > 0


def test_names_are_drawn_from_fixed_pools():
    from persona_engine import name_pools

    persona = _generate()

    assert persona.first_name in name_pools.FIRST_NAMES
    assert persona.last_name in name_pools.LAST_NAMES


def test_generation_varies_across_calls():
    personas = [_generate() for _ in range(20)]
    attribute_tuples = {
        (p.first_name, p.last_name, p.age, p.gender, p.geography, p.income)
        for p in personas
    }

    assert len(attribute_tuples) > 1


def test_seeded_rng_reproduces_output():
    from persona_engine import PersonaGenerator

    config = _default_config()
    seeded_first = PersonaGenerator(random.Random(42)).generate(config)
    seeded_second = PersonaGenerator(random.Random(42)).generate(config)

    assert seeded_first == seeded_second


def test_all_attributes_within_configured_ranges():
    config = _default_config(age_range=(30, 40), income_range=(50_000, 60_000))

    personas = [_generate(config) for _ in range(200)]

    for persona in personas:
        assert 30 <= persona.age <= 40
        assert persona.gender in config.genders
        assert persona.geography in config.geographies
        assert 50_000 <= persona.income <= 60_000


def test_geography_is_synthetic_pool_member():
    synthetic_geographies = ["Region Alpha", "Region Beta", "Region Gamma"]
    config = _default_config(geographies=synthetic_geographies)

    geographies = {_generate(config).geography for _ in range(100)}

    assert config.geographies
    assert geographies <= set(config.geographies)


@pytest.mark.parametrize(
    "inverted_field",
    ["age_range", "income_range"],
)
def test_invalid_ranges_raise_loudly(inverted_field):
    from persona_engine import GenerationConfig

    invalid_bounds = {"age_range": (40, 30), "income_range": (60_000, 50_000)}

    with pytest.raises(ValueError):
        GenerationConfig(**{inverted_field: invalid_bounds[inverted_field]})
