"""Synthetic persona generation engine.

Public API:
    Persona - the generated record
    GenerationConfig - the configured demographic ranges
    PersonaGenerator - generates a persona per call, or a reproducible dataset
    GeneratedDataset - the frozen record of one seeded generation run
    serialization - canonical bytes, manifests and replay for datasets
    name_pools - the committed synthetic name pools
    name_screening - the forbidden-value screen at the emission boundary
"""

from persona_engine import name_pools, name_screening, serialization
from persona_engine.configuration import GenerationConfig
from persona_engine.dataset import GeneratedDataset
from persona_engine.generator import PersonaGenerator
from persona_engine.persona import Persona

__all__ = [
    "Persona",
    "GenerationConfig",
    "PersonaGenerator",
    "GeneratedDataset",
    "serialization",
    "name_pools",
    "name_screening",
]
