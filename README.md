# Fuzzy Chain Saw

The Fuzzy Chain Saw repository holds the web application foundation — a React +
TypeScript + Vite + Tailwind single-page application served by a FastAPI
backend from one Docker image — and the persona engine that generates
synthetic test personas and repeatable datasets for it. Feature work lands in
this repository from sprint 1 onward behind CI that builds, tests and deploys
the skeleton to staging.

## Layout

- `frontend/` — the SPA (`src/`), its strict TypeScript config and its Vite config
- `backend/` — the FastAPI service (`app/` routes, settings, ASGI entrypoint) and its tests (`tests/`)
- `src/persona_engine/` — the synthetic persona engine (`src/layout`), with its suite in `tests/`
- `Dockerfile` — multi-stage image: Node builds the SPA, Python serves it
- `docker-compose.yml` — runtime composition for staging and local serving
- `.github/workflows/ci.yml` — the merge-to-main pipeline

## Configuration

All configuration resolves from the environment (`backend/app/settings.py`).
`APP_NAME` and `ENVIRONMENT` are required: a process started without them
fails loudly before serving traffic. `SPA_DIRECTORY` points the backend at a
built SPA bundle; the Docker image bakes it as `/srv/app/frontend`. Secrets
never come from the repository — copy `.env.example` to `.env` for local
development only (`.env` is gitignored), and let staging resolve values from
its deployment environment.

## Run it locally

```sh
docker compose up --build   # serves the whole app on http://localhost:8000
```

## Backend development

```sh
python3 -m venv .venv && .venv/bin/pip install -e "backend[test]"
.venv/bin/pytest backend/tests --cov=app --cov-fail-under=80
.venv/bin/pyflakes backend/app backend/tests
.venv/bin/uvicorn app.asgi:app   # requires APP_NAME/ENVIRONMENT set
```

## Persona engine

The persona engine generates a single randomized synthetic person: a
first/last name drawn from fixed synthetic pools plus age, gender, geography
and income attributes. The output resembles sample member data but never
references a real member identity, because every value is drawn from
committed, synthetic pools and configured ranges.

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

### Repeatable datasets

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

### Persona engine tests

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

## Frontend development

```sh
npm install
npm run dev     # dev server for the SPA
npm run lint    # tsc --noEmit over frontend/
npm test        # vitest (unit + jest-axe accessibility)
npm run build   # production bundle in frontend/dist/
```

## CI/CD

On every merge to `main`, the workflow lints (pyflakes, tsc), runs both suites
under a hard 80% coverage gate, builds the image, pushes it to GHCR, deploys
to staging over SSH and smoke-checks the staging root URL (HTTP 200 plus the
home heading). Pull requests run lint and tests only. Staging deploy secrets
(`STAGING_HOST`, `STAGING_SSH_USER`, `STAGING_SSH_KEY`) and the
`STAGING_ROOT_URL` variable are configured in the repository settings; the
workflow refuses to run — it never fakes success — when they are absent.
