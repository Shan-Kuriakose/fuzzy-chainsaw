"""Acceptance tests for the per-attribute calibration report.

Each test maps to an acceptance criterion of the story:
AC2 - a calibration report documents, for each attribute, the observed
      share, the published reference share and the deviation between
      them - and attributes with no published census-style reference
      (names, synthetic geography) are documented as such rather than
      silently omitted
"""

import dataclasses

import pytest


def _generated_default_dataset():
    from persona_engine import GenerationConfig, PersonaGenerator

    config = GenerationConfig()
    return PersonaGenerator().generate_dataset(config, count=1_000, seed=7)


def _entries_by_attribute(dataset):
    from persona_engine import calibration

    return {
        entry.attribute: entry
        for entry in calibration.calibration_report(dataset)
    }


def test_calibration_report_documents_deviations_for_each_attribute():
    from persona_engine import Persona

    dataset = _generated_default_dataset()
    entries = _entries_by_attribute(dataset)

    persona_attributes = [
        field.name for field in dataclasses.fields(Persona)
    ]
    for attribute in persona_attributes:
        assert attribute in entries, (
            f"the calibration report must carry an entry for '{attribute}'"
        )

    for attribute in ("age", "gender", "income"):
        entry = entries[attribute]
        assert entry.observed_shares, (
            f"'{attribute}' must report its observed shares"
        )
        assert entry.reference_shares, (
            f"'{attribute}' must carry the published reference shares"
        )
        assert set(entry.reference_shares) <= set(entry.observed_shares), (
            f"'{attribute}' must observe every reference category"
        )
        assert set(entry.reference_shares) <= set(entry.deviations), (
            f"'{attribute}' must document a deviation for every reference category"
        )
        for category, reference in entry.reference_shares.items():
            expected_deviation = entry.observed_shares[category] - reference
            assert entry.deviations[category] == pytest.approx(
                expected_deviation, abs=1e-6
            )


def test_calibration_report_documents_attributes_without_a_published_reference():
    dataset = _generated_default_dataset()
    entries = _entries_by_attribute(dataset)

    for attribute in ("first_name", "last_name", "geography"):
        entry = entries[attribute]
        assert not entry.has_published_reference, (
            f"'{attribute}' is a synthetic attribute with no census-style "
            "reference, so the report must not claim one"
        )
        assert entry.reference_shares is None, (
            f"'{attribute}' must carry no reference shares"
        )
        assert entry.no_reference_note.strip(), (
            f"the report must state explicitly that '{attribute}' has no "
            "published reference, rather than omitting it"
        )
