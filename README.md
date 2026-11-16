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

## Repeatable datasets

`generate_dataset(config, count, *, seed)` produces a whole dataset from one
seed. The seed is required: the same seed and the same configuration rebuild
the exact same dataset, byte for byte.

```python
from persona_engine import GenerationConfig, PersonaGenerator, serialization

config = GenerationConfig(age_range=(25, 45), geographies=("Region Alpha",))
dataset = PersonaGenerator().generate_dataset(config, count=100, seed=2026)

# Canonical bytes embed the seed, configuration, count, manifest version and
# the Python version of the run, so the dataset is self-recording:
saved = serialization.to_json_bytes(dataset)

# Replay a saved dataset later (the QA defect-reproduction workflow):
manifest = serialization.manifest_from_bytes(saved)
reproduced = serialization.replay(manifest)
assert reproduced.personas == dataset.personas
```

A dataset that produced a defect is a failing test you can keep: save its
bytes next to the defect report, and any developer rerun of the same seed and
configuration reproduces the failing records exactly.

Byte identity holds per Python runtime: `random.Random`'s output is stable
within an interpreter version but is not guaranteed across Python versions.
The manifest records `python_version` and `manifest_version`, so a
cross-runtime replay is visibly different rather than silently resolved, and
a manifest written by an unsupported manifest version is refused loudly.
`replay` also pins the variable consumption order: generation draws persona
attributes in a fixed sequence, so adding or reordering an attribute in a
future release changes every dataset and is announced by bumping
`manifest_version`.

## Running the tests

From a clean checkout, with a Python 3.10+ interpreter and no network access
beyond the initial dependency install:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest --cov=persona_engine
```

The 80% coverage floor from the engineering standard is enforced by
`fail_under = 80` in the `[tool.coverage.report]` section of
`pyproject.toml`, so the command above fails when coverage drops below it.

Test-only dependencies (`pytest`, `pytest-cov`) are declared in the `dev`
extra of `pyproject.toml`.
