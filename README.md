# persona-engine

Generates a single randomized synthetic person: a first/last name drawn from
fixed synthetic pools plus age, gender, geography and income attributes. The
output resembles sample member data but never references a real member
identity, because every value is drawn from committed, synthetic pools and
configured ranges.

## Usage

```python
from persona_engine import GenerationConfig, PersonaGenerator

generator = PersonaGenerator()
persona = generator.generate(GenerationConfig())

# Deterministic output for tests, by injecting a seeded random source:
import random
reproducible = PersonaGenerator(random.Random(42)).generate(
    GenerationConfig(age_range=(30, 40), income_range=(50_000, 60_000))
)
```

## Running the tests

From a clean checkout, with a Python 3.10+ interpreter and no network access
beyond the initial dependency install:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest --cov=persona_engine
```

Test-only dependencies (`pytest`, `pytest-cov`) are declared in the `dev`
extra of `pyproject.toml`.
