"""PersonaGenerator: turns a GenerationConfig into a synthetic Persona."""

import random

from persona_engine import name_pools
from persona_engine.configuration import GenerationConfig
from persona_engine.persona import Persona


class PersonaGenerator:
    """Generates one synthetic persona per call, within configured ranges.

    The random source is injectable so tests can seed it for reproducible
    output; leaving it unseeded makes every generation vary.
    """

    def __init__(self, rng: random.Random | None = None):
        self._rng = rng if rng is not None else random.Random()

    def generate(self, config: GenerationConfig) -> Persona:
        return Persona(
            first_name=self._rng.choice(name_pools.FIRST_NAMES),
            last_name=self._rng.choice(name_pools.LAST_NAMES),
            age=self._number_within(config.age_range),
            gender=self._rng.choice(list(config.genders)),
            geography=self._rng.choice(list(config.geographies)),
            income=self._number_within(config.income_range),
        )

    def _number_within(self, bounds: tuple[int, int]) -> int:
        low, high = bounds
        return self._rng.randint(low, high)
