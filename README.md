# persona-engine

Generates a single randomized synthetic person: a first/last name drawn from
fixed synthetic pools plus age, gender, geography and income attributes. The
output resembles sample member data but never references a real member
identity, because every value is drawn from committed, synthetic pools and
configured ranges.

## Engine usage

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

## Saving, sharing and reusing dataset configurations

The Fuzzy Chain Saw web application adds named dataset configurations. A
configuration is the boundary payload (`age_range`, `genders`, `geographies`,
`income_range`) plus the `count` and the required `seed`; saving it generates
the dataset server-side and stores the canonical serialization bytes with the
name and team.

### The seed contract

A configuration is reproducible because its seed is recorded. The saved
dataset bytes embed the seed, the configuration, the count, the manifest
version and the Python version of the run. Reproducing loads the stored
bytes and replays them: records are verified against the rows the bytes
record and a divergent replay (a different runtime, a stale pool, a
tampered artifact) fails loudly instead of returning something else.
Byte identity therefore holds within a single Python runtime; the stored
bytes make the boundary explicit rather than silent.

### HTTP endpoints

All dataset configuration endpoints are scoped by team; a configuration
saved into a team is listed and reproducible by anyone acting for that
team, and invisible from other teams.

| Method | Path | Behaviour |
| --- | --- | --- |
| `PUT` | `/api/teams/{team}/dataset-configurations` | Save `{name, count, seed, configuration}`; `201`, or `409` when the team already holds that name |
| `GET` | `/api/teams/{team}/dataset-configurations` | List the team's saved configurations |
| `GET` | `/api/teams/{team}/dataset-configurations/{name}` | Retrieve one saved configuration, `404` when unsaved |
| `GET` | `/api/teams/{team}/dataset-configurations/{name}/reproduce` | Regenerate the exact records, `404` when unsaved |

Team scoping is request-supplied, without authentication; real membership
and authentication are deferred concerns. The storage port
(`backend/app/storage/repository.py`) is the seam to introduce them.

### Storage

Saved configurations live in PostgreSQL via SQLAlchemy, created by the
versioned Alembic migrations in `backend/migrations/` (applied when the
service builds, reversible to base). In tests and CI the backend suite
runs against SQLite through the same repository and migration code.

## The web application

```sh
cp .env.example .env   # choose a POSTGRES_PASSWORD and matching DATABASE_URL
docker compose up --build
```

The app serves the SPA on port 8000; the `Dataset configurations` page
(save form, the team's saved list, reproduce to the exact records) is
reachable from the primary navigation.

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

## Running the tests

Backend (Python 3.11+, from the repository root):

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e . -e "./backend[test]"
pytest backend/tests tests --cov=app --cov=persona_engine
```

Frontend (Node 20+):

```sh
npm install
npm test
```

The 80% coverage floor from the engineering standard is enforced in CI
(`--cov-fail-under=80` for the backend, coverage thresholds for the
frontend) and by `fail_under = 80` for the engine itself.

Test-only dependencies (`pytest`, `pytest-cov`, `pyflakes`) are declared in
the `test` extra of `backend/pyproject.toml` and the `dev` extra of
`pyproject.toml`.

