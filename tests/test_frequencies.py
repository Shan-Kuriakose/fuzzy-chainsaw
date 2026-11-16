"""Acceptance tests for summarizing generated attribute frequencies (AC2).

Each test maps to an acceptance criterion of the story:
AC2 - given a generated dataset, when its attribute frequencies are
      summarized, then they match the configured distributions within a
      defined tolerance.
"""

from persona_engine.persona import Persona


def _persona(age, gender, geography, income):
    return Persona(
        first_name="Example",
        last_name="Placeholder",
        age=age,
        gender=gender,
        geography=geography,
        income=income,
    )


def test_frequency_summarization_reports_category_and_bin_shares():
    from persona_engine.distributions import PopulationDistributions
    from persona_engine.frequencies import SHARE_TOLERANCE, attribute_shares

    distributions = PopulationDistributions(
        age_bins=((20, 29), (30, 39)),
        age_weights=(0.5, 0.5),
        income_bins=((20_000, 39_999), (40_000, 80_000)),
        income_weights=(0.5, 0.5),
        gender_weights=(0.75, 0.25),
        geography_weights=(0.5, 0.5),
    )
    personas = (
        _persona(20, "Female", "Region Alpha", 25_000),
        _persona(25, "Female", "Region Alpha", 30_000),
        _persona(28, "Female", "Region Beta", 35_000),
        _persona(31, "Male", "Region Beta", 45_000),
    )

    summary = attribute_shares(personas, distributions)

    assert summary["gender"] == {"Female": 0.75, "Male": 0.25}
    assert summary["geography"] == {
        "Region Alpha": 0.75,
        "Region Beta": 0.25,
    }
    assert summary["age"] == [(20, 29, 0.75), (30, 39, 0.25)]
    assert summary["income"] == [(20_000, 39_999, 0.75), (40_000, 80_000, 0.25)]
    assert SHARE_TOLERANCE == 0.02


def test_seeded_dataset_matches_configured_distributions_within_two_percentage_points():
    from persona_engine import GenerationConfig, PersonaGenerator
    from persona_engine.frequencies import SHARE_TOLERANCE, attribute_shares

    config = GenerationConfig()
    dataset = PersonaGenerator().generate_dataset(config, count=10_000, seed=46)
    configured = config.distributions

    summary = attribute_shares(dataset.personas, configured)

    _assert_bin_shares_hold(summary["age"], configured.age_weights)
    _assert_bin_shares_hold(summary["income"], configured.income_weights)
    _assert_category_shares_hold(
        config.genders, configured.gender_weights, summary["gender"], SHARE_TOLERANCE
    )
    _assert_category_shares_hold(
        config.geographies,
        configured.geography_weights,
        summary["geography"],
        SHARE_TOLERANCE,
    )


def _assert_bin_shares_hold(observed_bins, configured_weights):
    from persona_engine.frequencies import SHARE_TOLERANCE

    for index, (low, high, share) in enumerate(observed_bins):
        configured = configured_weights[index]
        assert abs(share - configured) <= SHARE_TOLERANCE, (
            f"bin ({low}, {high}) held {share:.3f} against a configured "
            f"weight of {configured}"
        )


def _assert_category_shares_hold(
    categories, configured_weights, observed_shares, tolerance
):
    for category, share in observed_shares.items():
        configured = configured_weights[categories.index(category)]
        assert abs(share - configured) <= tolerance, (
            f"category {category} held {share:.3f} against a configured "
            f"weight of {configured}"
        )
