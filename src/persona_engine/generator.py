"""PersonaGenerator: turns a GenerationConfig into synthetic Personas."""

import random

from persona_engine import name_pools
from persona_engine.configuration import GenerationConfig
from persona_engine.dataset import GeneratedDataset
from persona_engine.persona import Persona


class PersonaGenerator:
    """Generates synthetic personas within configured ranges.

    The random source is injectable so tests can seed it for reproducible
    output; leaving it unseeded makes every generation vary.
    """

    def __init__(self, rng: random.Random | None = None):
        self._rng = rng if rng is not None else random.Random()

    def generate(self, config: GenerationConfig) -> Persona:
        return self._persona_from(self._rng, config)

    def generate_dataset(
        self,
        config: GenerationConfig,
        count: int,
        *,
        seed: int,
    ) -> GeneratedDataset:
        """Generate `count` personas reproducibly from one seed.

        The seed is required: every persona is drawn from a dedicated
        random.Random(seed) in a fixed consumption order, so the same seed
        and configuration rebuild the exact dataset.
        """

        rng = random.Random(seed)
        personas = tuple(
            self._persona_from(rng, config) for _ in range(count)
        )
        return GeneratedDataset(seed=seed, configuration=config, personas=personas)

    @staticmethod
    def _persona_from(rng: random.Random, config: GenerationConfig) -> Persona:
        return Persona(
            first_name=rng.choice(name_pools.FIRST_NAMES),
            last_name=rng.choice(name_pools.LAST_NAMES),
            age=PersonaGenerator._number_within(rng, config.age_range),
            gender=rng.choice(list(config.genders)),
            geography=rng.choice(list(config.geographies)),
            income=PersonaGenerator._number_within(rng, config.income_range),
        )

    @staticmethod
    def _number_within(rng: random.Random, bounds: tuple[int, int]) -> int:
        low, high = bounds
        return rng.randint(low, high)
