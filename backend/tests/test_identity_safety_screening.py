"""Unit tests for the identity-safety screening policy and its file adapter.

The screen is a pure policy: given a generated batch and the list, it
decides a verdict without I/O. The file adapter is the concrete input
behind it: it reads the compliance-supplied list, and a missing list file
fails loudly rather than screening against nothing.
"""

import pytest

FORBIDDEN_GEOGRAPHY = "Region North"


def _batch_row(**overrides):
    row = {
        "first_name": "Avery",
        "last_name": "Ashford",
        "age": 34,
        "gender": "Female",
        "geography": "Region South",
        "income": 52_000,
    }
    row.update(overrides)
    return row


def test_screen_reports_match_when_a_batch_value_equals_a_forbidden_value():
    from app.dataset_configurations.identity_safety import ForbiddenValues, screen

    verdict = screen(
        [_batch_row(geography=FORBIDDEN_GEOGRAPHY)],
        ForbiddenValues(values=[FORBIDDEN_GEOGRAPHY]),
    )

    assert verdict.passed is False
    assert verdict.matched_values == [FORBIDDEN_GEOGRAPHY]


def test_screen_passes_a_clean_batch_and_matches_case_insensitively():
    from app.dataset_configurations.identity_safety import ForbiddenValues, screen

    forbidden = ForbiddenValues(values=[FORBIDDEN_GEOGRAPHY])

    clean_verdict = screen([_batch_row()], forbidden)
    case_variant_verdict = screen(
        [_batch_row(geography=FORBIDDEN_GEOGRAPHY.lower())], forbidden
    )

    assert clean_verdict.passed is True
    assert case_variant_verdict.passed is False


def test_screen_on_empty_list_passes_boundary_case():
    from app.dataset_configurations.identity_safety import ForbiddenValues, screen

    verdict = screen(
        [_batch_row(geography="whatever the batch holds")],
        ForbiddenValues(values=[]),
    )

    assert verdict.passed is True


def test_missing_forbidden_values_file_fails_the_screen_loudly(tmp_path):
    from app.dataset_configurations.file_forbidden_values import FileForbiddenValues

    adapter = FileForbiddenValues(tmp_path / "forbidden-values.json")

    with pytest.raises(FileNotFoundError):
        adapter.current()
