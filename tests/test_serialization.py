"""Serialization tests: canonical bytes, manifest decoding and refusals."""

import json

import pytest


def _seeded_dataset():
    from persona_engine import GenerationConfig

    config = GenerationConfig(age_range=(19, 62), geographies=("Region Alpha",))
    from persona_engine import PersonaGenerator

    return PersonaGenerator().generate_dataset(config, count=5, seed=11)


def test_manifest_from_bytes_decodes_the_payload_it_received():
    from persona_engine import serialization

    saved = serialization.to_json_bytes(_seeded_dataset())
    manifest = serialization.manifest_from_bytes(saved)

    assert manifest.seed == 11
    assert manifest.count == 5
    assert manifest.manifest_version == serialization.MANIFEST_VERSION
    assert list(manifest.personas) == json.loads(saved.decode("utf-8"))["personas"]


def test_replay_refuses_a_manifest_from_an_unsupported_version():
    from persona_engine import serialization

    stale_manifest = serialization.DatasetManifest(
        seed=1,
        count=1,
        manifest_version=serialization.MANIFEST_VERSION + 1,
        python_version="0.0.0",
        configuration={},
        personas=(),
    )

    with pytest.raises(ValueError):
        serialization.replay(stale_manifest)


def test_replay_refuses_records_that_diverge_from_the_saved_rows():
    from persona_engine import serialization

    manifest = serialization.manifest_from_bytes(
        serialization.to_json_bytes(_seeded_dataset())
    )
    corrupted_rows = list(manifest.personas)
    corrupted_rows[0] = {**corrupted_rows[0], "first_name": "Tampered"}
    cross_runtime_manifest = serialization.DatasetManifest(
        seed=manifest.seed,
        count=manifest.count,
        manifest_version=manifest.manifest_version,
        python_version=manifest.python_version,
        configuration=manifest.configuration,
        personas=tuple(corrupted_rows),
    )

    with pytest.raises(ValueError, match="not the saved ones"):
        serialization.replay(cross_runtime_manifest)


def test_replay_names_the_two_runtimes_in_a_divergence_error():
    from persona_engine import serialization

    manifest = serialization.manifest_from_bytes(
        serialization.to_json_bytes(_seeded_dataset())
    )
    corrupted_rows = list(manifest.personas)
    corrupted_rows[0] = {**corrupted_rows[0], "income": corrupted_rows[0]["income"] + 1}
    cross_runtime_manifest = serialization.DatasetManifest(
        seed=manifest.seed,
        count=manifest.count,
        manifest_version=manifest.manifest_version,
        python_version="1.2.3",
        configuration=manifest.configuration,
        personas=tuple(corrupted_rows),
    )

    with pytest.raises(ValueError, match="1.2.3"):
        serialization.replay(cross_runtime_manifest)
