"""Acceptance tests for the forbidden-name screen at the emission boundary.

Each test maps to acceptance criterion AC2 of the story: no generated name
is emitted when one of its components matches compliance's periodically
updated, non-PHI forbidden-value list. Every value here is obviously
synthetic and injected through a temporary file; the real compliance list
never travels with the repository.
"""

import pytest


def _forbidden_list(tmp_path, *values):
    from persona_engine.name_screening import ForbiddenValueList

    list_file = tmp_path / "compliance-forbidden-values.txt"
    list_file.write_text("\n".join(values) + "\n", encoding="utf-8")
    return ForbiddenValueList.from_file(list_file)


def _dataset_with(first_name, last_name):
    from persona_engine import GenerationConfig, GeneratedDataset, Persona

    persona = Persona(
        first_name=first_name,
        last_name=last_name,
        age=40,
        gender="Female",
        geography="Region North",
        income=50_000,
    )
    return GeneratedDataset(
        seed=3, configuration=GenerationConfig(), personas=(persona,)
    )


def test_forbidden_first_or_last_component_refuses_emission(tmp_path):
    from persona_engine import serialization
    from persona_engine.name_screening import ForbiddenNameError

    dataset = _dataset_with("Elmore", "Vandermeer")
    emission_surfaces = (
        serialization.to_json_bytes,
        serialization.to_csv_bytes,
        serialization.to_json_records_bytes,
    )

    for surface in emission_surfaces:
        with pytest.raises(ForbiddenNameError):
            surface(
                dataset,
                forbidden_values=_forbidden_list(tmp_path, "Elmore", "Huxley"),
            )

        with pytest.raises(ForbiddenNameError):
            surface(
                dataset,
                forbidden_values=_forbidden_list(tmp_path, "Vandermeer"),
            )


def test_screen_match_is_case_insensitive(tmp_path):
    from persona_engine import serialization
    from persona_engine.name_screening import ForbiddenNameError

    dataset = _dataset_with("Elmore", "Vandermeer")

    with pytest.raises(ForbiddenNameError):
        serialization.to_json_bytes(
            dataset,
            forbidden_values=_forbidden_list(tmp_path, "ELMORE"),
        )

    with pytest.raises(ForbiddenNameError):
        serialization.to_csv_bytes(
            dataset,
            forbidden_values=_forbidden_list(tmp_path, "vandermeer"),
        )


def test_clean_dataset_emission_is_unchanged_by_screening(tmp_path):
    from persona_engine import GenerationConfig, PersonaGenerator, serialization

    dataset = PersonaGenerator().generate_dataset(
        GenerationConfig(), count=10, seed=5
    )
    clean_list = _forbidden_list(tmp_path, "Norbert", "Gertrude")

    assert (
        serialization.to_json_bytes(dataset, forbidden_values=clean_list)
        == serialization.to_json_bytes(dataset)
    )
    assert (
        serialization.to_csv_bytes(dataset, forbidden_values=clean_list)
        == serialization.to_csv_bytes(dataset)
    )
    assert (
        serialization.to_json_records_bytes(dataset, forbidden_values=clean_list)
        == serialization.to_json_records_bytes(dataset)
    )


def test_updated_list_fails_replay_reemission_loudly(tmp_path):
    from persona_engine import serialization
    from persona_engine.name_screening import ForbiddenNameError

    dataset = _dataset_with("Elmore", "Vandermeer")
    saved = serialization.to_json_bytes(dataset)
    replayed = serialization.replay(serialization.manifest_from_bytes(saved))
    updated_list = _forbidden_list(tmp_path, "Elmore")

    with pytest.raises(ForbiddenNameError):
        serialization.to_json_bytes(replayed, forbidden_values=updated_list)


def test_empty_forbidden_list_is_refused(tmp_path):
    from persona_engine.name_screening import ForbiddenValueList

    empty_list_file = tmp_path / "compliance-forbidden-values.txt"
    empty_list_file.write_text("", encoding="utf-8")

    with pytest.raises(ValueError):
        ForbiddenValueList.from_file(empty_list_file)


def test_missing_list_file_raises(tmp_path):
    from persona_engine.name_screening import ForbiddenValueList

    with pytest.raises(OSError):
        ForbiddenValueList.from_file(
            tmp_path / "compliance-forbidden-values.txt"
        )
