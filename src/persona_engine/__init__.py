"""Synthetic persona generation engine.

Public API:
    Persona - the generated record
    GenerationConfig - the configured demographic ranges
    PersonaGenerator - generates a persona per call
    name_pools - the committed synthetic name pools
"""

from persona_engine import name_pools
from persona_engine.configuration import GenerationConfig
from persona_engine.generator import PersonaGenerator
from persona_engine.persona import Persona

__all__ = ["Persona", "GenerationConfig", "PersonaGenerator", "name_pools"]
