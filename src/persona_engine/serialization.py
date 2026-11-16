"""Serialization: the boundary where a GeneratedDataset becomes bytes.

This module owns all format knowledge. Records stay pure; everything
about JSON shape, canonical byte emission, manifest structure and
replay lives here.
"""

import json
import platform
from dataclasses import dataclass

from persona_engine.configuration import GenerationConfig
from persona_engine.dataset import GeneratedDataset
from persona_engine.generator import PersonaGenerator

MANIFEST_VERSION = 1


@dataclass(frozen=True)
class DatasetManifest:
    """A decoded dataset manifest, ready to be replayed."""

    seed: int
    count: int
    manifest_version: int
    python_version: str
    configuration: dict
    personas: tuple


def dataset_manifest(dataset: GeneratedDataset) -> dict:
    """Return the manifest payload a dataset is recorded as."""

    return {
        "seed": dataset.seed,
        "count": len(dataset.personas),
        "manifest_version": MANIFEST_VERSION,
        "python_version": platform.python_version(),
        "configuration": dataset.configuration.to_payload(),
        "personas": [persona.to_payload() for persona in dataset.personas],
    }


def to_json_bytes(dataset: GeneratedDataset) -> bytes:
    """Emit the canonical JSON encoding of a dataset's manifest."""

    return json.dumps(
        dataset_manifest(dataset),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def manifest_from_bytes(saved: bytes) -> DatasetManifest:
    """Decode saved dataset bytes back into a manifest."""

    payload = json.loads(saved.decode("utf-8"))
    return DatasetManifest(
        seed=payload["seed"],
        count=payload["count"],
        manifest_version=payload["manifest_version"],
        python_version=payload["python_version"],
        configuration=payload["configuration"],
        personas=tuple(payload["personas"]),
    )


def replay(manifest: DatasetManifest) -> GeneratedDataset:
    """Regenerate the dataset a saved manifest was built from."""

    _refuse_unsupported_manifest(manifest)
    configuration = GenerationConfig.from_payload(manifest.configuration)
    return PersonaGenerator().generate_dataset(
        configuration,
        count=manifest.count,
        seed=manifest.seed,
    )


def _refuse_unsupported_manifest(manifest: DatasetManifest) -> None:
    if manifest.manifest_version != MANIFEST_VERSION:
        raise ValueError(
            "cannot replay manifest version "
            f"{manifest.manifest_version}: this engine writes version "
            f"{MANIFEST_VERSION}"
        )
