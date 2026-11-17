"""Acceptance tests for census-style calibrated distributions.

Each test maps to an acceptance criterion of the story:
AC1 - a generated dataset's distribution summaries fall within tolerance
      of the hardcoded published census-style reference statistics, and
      weighted draws stay within overridden configured ranges
"""

import random

# The AC1 tolerance is statistically honest only at a pinned sample size,
# so the acceptance test fixes both the count and the seed.
DEFAULT_SEED = 20260101
DEFAULT_COUNT = 10_000


def _generated_default_dataset():
    from persona_engine import GenerationConfig, PersonaGenerator

    config = GenerationConfig()
    return PersonaGenerator().generate_dataset(
        config, count=DEFAULT_COUNT, seed=DEFAULT_SEED
    )


def _entries_by_attribute(dataset):
    from persona_engine import calibration

    return {
        entry.attribute: entry
        for entry in calibration.calibration_report(dataset)
    }


def test_default_configuration_dataset_summaries_fall_within_published_reference_tolerance():
    from persona_engine import reference_population

    entries = _entries_by_attribute(_generated_default_dataset())

    for attribute, tolerance in reference_population.TOLERANCE_PERCENTAGE_POINTS.items():
        entry = entries[attribute]
        assert entry.reference_shares is not None, (
            f"attribute '{attribute}' must be compared against a "
            "published reference"
        )
        worst_deviation = max(
            abs(entry.deviations[category])
            for category in entry.reference_shares
        )
        assert worst_deviation <= tolerance, (
            f"attribute '{attribute}' deviates {worst_deviation} percentage "
            f"points from its published reference, above the {tolerance} tolerance"
        )


def test_weighted_draws_stay_within_configured_ranges():
    from persona_engine import distribution

    rng = random.Random(5)
    edge_age_ranges = [(40, 45), (18, 19), (84, 85)]
    for low, high in edge_age_ranges:
        drawn_ages = [distribution.weighted_age(rng, (low, high)) for _ in range(50)]
        assert all(low <= age <= high for age in drawn_ages), (
            f"a weighted age draw fell outside the overridden range ({low}, {high})"
        )

    income_low, income_high = 80_000, 85_000
    drawn_incomes = [
        distribution.weighted_income(rng, (income_low, income_high))
        for _ in range(50)
    ]
    assert all(income_low <= income <= income_high for income in drawn_incomes), (
        "a weighted income draw fell outside the overridden bracket range"
    )

    for _ in range(20):
        assert distribution.weighted_gender(rng, ("Female",)) == "Female", (
            "a weighted gender draw ignored the overridden category list"
        )
