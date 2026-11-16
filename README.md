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
`replay` therefore verifies the regenerated records against the rows the
manifest itself recorded and refuses loudly when they diverge — a
cross-runtime mismatch is an exception at the call site, never a silently
different dataset. The manifest carries the `python_version` and
`manifest_version` of the run that wrote it, so the error message names both
runtimes, and a manifest of an unsupported manifest version is refused
outright.
`replay` also pins the variable consumption order: generation draws persona
attributes in a fixed sequence, so adding or reordering an attribute in a
future release changes every dataset and is announced by bumping
`manifest_version`.

## Exporting datasets for dashboards and pipelines

Once a dataset is generated, two exports carry its records to downstream
tools without any real member identity: every value comes from the
committed name pools or the configured ranges, the same as generation.

```python
from persona_engine import GenerationConfig, PersonaGenerator, serialization

config = GenerationConfig(age_range=(25, 45), geographies=("Region Alpha",))
dataset = PersonaGenerator().generate_dataset(config, count=100, seed=2026)

# CSV: a header row naming Persona's fields, then one row per persona.
# Fields arrive as strings (CSV is typeless); the header documents the
# schema downstream tools import against.
csv_bytes = serialization.to_csv_bytes(dataset)

# JSON: a bare array of flat records with types preserved (age and
# income are numbers).
json_bytes = serialization.to_json_records_bytes(dataset)
```

These records exports are the BI/load surface: dashboards and pipelines
import them directly. The manifest bytes from `to_json_bytes` remain the
defect-replay surface — they add the seed, configuration and envelope a
`replay` needs, which an import into a BI tool does not want.

Two things to know about the schema:

- The CSV header follows Persona's fields, so a change to those fields
  changes the export, the way a `manifest_version` bump does.
- CSV carries no types; JSON is the typed export. For CSV, downstream
  tools type `age` and `income` as numbers per the header's documented
  schema.

## Name screening

Generated names cannot reference a real member identity by construction:
every first and last name is drawn from the fixed synthetic pools
committed in `src/persona_engine/name_pools.py`, and the generator
combines one pool entry of each, so no name outside
`FIRST_NAMES x LAST_NAMES` can ever appear in a generated record.

By construction alone is not the whole guarantee, though: compliance
maintains a periodically updated, non-PHI list of forbidden values — any
value that, for whatever reason, must never appear in an emitted dataset.
The screening mechanism is the last gate before bytes leave the engine.
Every export surface (`to_json_bytes`, `to_csv_bytes`,
`to_json_records_bytes`) accepts an optional `forbidden_values` argument
carrying a `ForbiddenValueList`; if a persona's first or last name
matches a listed value, exactly and case-insensitively, the emission
raises `ForbiddenNameError` and no bytes are produced.

The list is a plain text file with one value per line, loaded with
`ForbiddenValueList.from_file`:

```python
from persona_engine import serialization
from persona_engine.name_screening import ForbiddenValueList

forbidden = ForbiddenValueList.from_file("compliance-forbidden-values.txt")
csv_bytes = serialization.to_csv_bytes(dataset, forbidden_values=forbidden)
```

Three properties of the mechanism matter to a reviewer:

- **The list is never committed to this repository.** It carries
  real-identity-shaped values by design, so it travels with compliance
  and is supplied at the emission call site. Nothing in the checkout —
  source, fixtures or tests — may hold it.
- **The screen never redraws or substitutes a name.** It refuses or
  passes, and touches no random source, so a seeded dataset stays a pure
  function of seed, pools and configuration, and `replay`'s
  byte-identical contract is untouched.
- **An updated list can refuse a saved dataset later.** Passing a list
  updated since the dataset was generated can make its re-emission raise
  `ForbiddenNameError`. That is the intended, safety-correct outcome:
  a dataset whose names a new list forbids must fail loudly, never emit
  silently.

Screening is offered at the emission boundary rather than inside
generation so keepers of saved manifests can decide when a list update
applies to re-export; the README emission examples above remain valid
without a list, and the screen is a deliberate choice the emitting call
site makes visible.

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
