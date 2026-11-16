"""Acceptance tests for unrealistic-population warnings (AC3, engine side).

Each test maps to an acceptance criterion of the story:
AC3 - given a configuration that would produce an unrealistic or invalid
      population, the engine-side realism policy surfaces a warning
      before generation proceeds; valid but unusual weights are still a
      recognized pattern, so invalid weight bundles stay a hard refusal
      (covered by tests/test_distributions.py).
"""

def _weighted_bundle_for(**overrides):
    from persona_engine.distributions import PopulationDistributions

    group_defaults = {
        "age_bins": ((18, 39), (40, 85)),
        "age_weights": (0.5, 0.5),
        "income_bins": ((20_000, 60_000), (60_001, 150_000)),
        "income_weights": (0.5, 0.5),
        "gender_weights": (0.5, 0.5),
        "geography_weights": (0.5, 0.5),
    }
    group_defaults.update(overrides)
    return PopulationDistributions(**group_defaults)


def _built_config(**overrides):
    from persona_engine import GenerationConfig

    return GenerationConfig(**overrides)


def _geography_weights_for(count, concentrated_index, concentration):
    weights = [(1.0 - concentration) / (count - 1)] * count
    weights[concentrated_index] = concentration
    return tuple(weights)


def test_concentrated_attribute_warns_as_unrealistic():
    from persona_engine.realism import realism_warnings

    config = _built_config(
        genders=("Female", "Male"),
        geographies=("Region Alpha", "Region Beta", "Region Gamma"),
        distributions=_weighted_bundle_for(
            gender_weights=(0.95, 0.05),
            geography_weights=_geography_weights_for(3, 0, 0.4),
        ),
    )

    warnings = realism_warnings(config)

    assert warnings, "a 95% single-gender population must draw a warning"
    assert any("gender" in warning.lower() for warning in warnings)


def test_frame_outside_published_coverage_warns():
    from persona_engine.realism import realism_warnings

    config = _built_config(age_range=(105, 120))

    warnings = realism_warnings(config)

    assert warnings, "an age frame beyond published coverage must draw a warning"
    assert any("age" in warning.lower() for warning in warnings)


def test_balanced_configuration_warns_nothing():
    from persona_engine.realism import realism_warnings

    config = _built_config()

    assert not realism_warnings(config)
