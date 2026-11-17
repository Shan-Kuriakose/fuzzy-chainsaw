"""Acceptance tests for identity-safety screening of generated datasets.

Each test maps to behavior the story must carry:
- a ValueScreen refuses any forbidden value case-insensitively, saying
  what was refused;
- a screen that carries no generated value passes the synthetic name
  pools and the default configuration untouched;
- screening a whole dataset checks every generated string value,
  including the names, the gender labels and the geography labels.

Forbidden values in these tests are obviously synthetic placeholders
and names deliberately drawn from the committed fixed name pools.
"""

import pytest


def screen_refusing(*values):
    from persona_engine.screening import ValueScreen

    return ValueScreen(values)


def _default_dataset(count):
    from persona_engine import GenerationConfig, PersonaGenerator

    return PersonaGenerator().generate_dataset(
        GenerationConfig(),
        count=count,
        seed=7,
    )


def test_screening_refuses_forbidden_values_case_insensitively():
    screen = screen_refusing("Forsaken Region", "Unlisted Gender")

    for forbidden_value in ("Forsaken Region", "forsaken region", "FORSAKEN REGION"):
        with pytest.raises(Exception) as refused:
            screen.screen(forbidden_value)
        assert type(refused.value).__name__ == "ForbiddenValueRefused"
        assert "forsaken region" in str(refused.value).lower()


def test_a_screen_passes_values_that_are_not_forbidden():
    screen = screen_refusing("Forsaken Region")

    screen.screen("Region North")


def test_screening_passes_synthetic_pool_names_and_the_default_configuration():
    from persona_engine import name_pools
    from persona_engine.configuration import GenerationConfig

    screen = screen_refusing("Forsaken Region", "Unlisted Gender")

    for pool_name in name_pools.FIRST_NAMES + name_pools.LAST_NAMES:
        screen.screen(pool_name)
    default_configuration = GenerationConfig()
    for gender in default_configuration.genders:
        screen.screen(gender)
    for geography in default_configuration.geographies:
        screen.screen(geography)
    screen.screen_dataset(_default_dataset(count=3))


def _generated_screened_dataset(count):
    from persona_engine import GenerationConfig, PersonaGenerator

    return PersonaGenerator().generate_dataset(
        GenerationConfig(
            genders=("Female", "Male"),
            geographies=("Region Alpha",),
        ),
        count=count,
        seed=7,
    )


def test_screening_checks_every_generated_string_value_including_names():
    dataset = _generated_screened_dataset(count=25)
    records = [persona.to_payload() for persona in dataset.personas]

    for field_name in ("first_name", "last_name", "gender", "geography"):
        generated_value = records[0][field_name]
        screen = screen_refusing(generated_value.casefold())

        with pytest.raises(Exception) as refused:
            screen.screen_dataset(dataset)

        assert type(refused.value).__name__ == "ForbiddenValueRefused"
        assert generated_value.casefold() in str(refused.value).lower()
