"""GeneratedDataset: the frozen record of one seeded generation run.

A dataset is the artifact reproducibility is judged on: it carries the
seed, the configuration and the personas a run produced, so the exact
output can be compared and replayed later.
"""

from dataclasses import dataclass

from persona_engine.configuration import GenerationConfig
from persona_engine.persona import Persona


@dataclass(frozen=True)
class GeneratedDataset:
    """One reproducible generation run: seed, configuration and personas."""

    seed: int
    configuration: GenerationConfig
    personas: tuple[Persona, ...]
