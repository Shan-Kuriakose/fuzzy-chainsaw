"""Acceptance tests for per-dataset demographic distributions (AC1).

Each test maps to an acceptance criterion of the story:
AC1 - given a dataset configuration, when distribution parameters are set
      per attribute (or left at the built-in published census-style
      defaults), then generated records follow the effective
      distributions, and configurations with invalid weights are refused.
"""

import pytest


def _weighted_bundle(**overrides):
    from persona_engine.distributions import PopulationDistributions

    group_defaults = {
        "age_bins": ((18, 39), (40, 85)),
        "age_weights": (0.9, 0.1),
        "income_bins": ((20_000, 60_000), (60_001, 150_000)),
        "income_weights": (0.35, 0.65),
        "gender_weights": (0.8, 0.1, 0.1),
        "geography_weights": (0.4, 0.3, 0.2, 0.1),
    }
    group_defaults.update(overrides)
    return PopulationDistributions(**group_defaults)


def _seeded_dataset(count, seed, **config_overrides):
    from persona_engine import GenerationConfig, PersonaGenerator

    config = GenerationConfig(**config_overrides)
    return PersonaGenerator().generate_dataset(config, count=count, seed=seed)


def _category_share(personas, attribute, category):
    matching = sum(1 for persona in personas if getattr(persona, attribute) == category)
    return matching / len(personas)


def test_default_config_uses_the_published_census_style_distributions():
    from persona_engine import GenerationConfig
    from persona_engine.distributions import census_defaults

    config = GenerationConfig()

    assert config.distributions == census_defaults()
    assert (
        len(set(config.distributions.age_weights)) > 1
    ), "the published census-style default must not be a uniform split"


def test_ages_are_drawn_from_weighted_bins_when_configured():
    young_bin, old_bin = (18, 39), (40, 85)
    bundle = _weighted_bundle(age_bins=(young_bin, old_bin), age_weights=(0.9, 0.1))

    dataset = _seeded_dataset(
        1_000,
        seed=11,
        age_range=(18, 85),
        genders=("Female", "Male", "Non-Binary"),
        distributions=bundle,
    )

    young_share = (
        sum(1 for persona in dataset.personas if persona.age <= 39) / 1_000
    )

    assert 0.84 <= young_share <= 0.96


def test_categories_follow_configured_weights_when_configured():
    genders = ("Female", "Male", "Non-Binary")
    geographies = ("Region Alpha", "Region Beta", "Region Gamma", "Region Delta")
    bundle = _weighted_bundle(
        age_bins=((18, 39), (40, 85)),
        age_weights=(0.5, 0.5),
        income_bins=((20_000, 60_000), (60_001, 150_000)),
        income_weights=(0.5, 0.5),
        gender_weights=(0.8, 0.1, 0.1),
        geography_weights=(0.4, 0.3, 0.2, 0.1),
    )

    dataset = _seeded_dataset(
        1_000,
        seed=23,
        genders=genders,
        geographies=geographies,
        distributions=bundle,
    )

    assert 0.74 <= _category_share(dataset.personas, "gender", "Female") <= 0.86
    assert 0.34 <= _category_share(dataset.personas, "geography", "Region Alpha") <= 0.46


def test_custom_frames_without_distributions_fall_back_to_uniform():
    from persona_engine import GenerationConfig

    config = GenerationConfig(
        age_range=(20, 60),
        genders=("Female", "Male"),
        geographies=("Region Alpha", "Region Beta"),
        income_range=(30_000, 40_000),
    )

    assert config.distributions is None

    dataset = _seeded_dataset(
        1_000,
        seed=5,
        age_range=(20, 60),
        genders=("Female", "Male"),
        geographies=("Region Alpha", "Region Beta"),
        income_range=(30_000, 40_000),
    )

    first_half_share = (
        sum(1 for persona in dataset.personas if persona.age <= 40) / 1_000
    )
    assert 0.40 <= first_half_share <= 0.60
    assert 0.40 <= _category_share(dataset.personas, "gender", "Female") <= 0.60


def test_weights_refused_when_mismatched_or_unsummed():
    from persona_engine import GenerationConfig
    from persona_engine.distributions import PopulationDistributions

    with pytest.raises(ValueError):
        GenerationConfig(
            genders=("Female", "Male", "Non-Binary"),
            distributions=_weighted_bundle(gender_weights=(0.8, 0.2)),
        )

    with pytest.raises(ValueError):
        GenerationConfig(
            age_range=(18, 85),
            distributions=_weighted_bundle(age_weights=(0.9, 0.05)),
        )

    with pytest.raises(ValueError):
        PopulationDistributions(gender_weights=(0.55, 0.55))
