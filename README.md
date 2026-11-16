# Fuzzy Chain Saw

The Fuzzy Chain Saw web application foundation: a React + TypeScript + Vite +
Tailwind single-page application served by a FastAPI backend from one Docker
image. Feature work lands here from sprint 1 onward behind CI that builds,
tests and deploys this skeleton to staging.

## Layout

- `frontend/` — the SPA (`src/`), its strict TypeScript config and its Vite config
- `backend/` — the FastAPI service (`app/` routes, settings, ASGI entrypoint) and its tests (`tests/`)
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
