from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes.dataset_configurations import build_dataset_configurations_router
from app.routes.health import health_router
from app.settings import Settings

TEST_APP_NAME = "fuzzy-chain-saw"
TEST_ENVIRONMENT = "test"
SPA_MOUNT_NAME = "spa"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application for injected configuration.

    Tests and local experiments call it without configuration and get the
    built-in test settings; a real deployment always injects ``Settings()``
    so that missing environment values fail loudly before serving traffic.
    """
    settings = settings or Settings(
        app_name=TEST_APP_NAME,
        environment=TEST_ENVIRONMENT,
    )
    application = FastAPI(title=settings.app_name)
    application.include_router(health_router)
    application.include_router(build_dataset_configurations_router(settings))
    if settings.spa_directory is not None:
        _serve_spa(application, Path(settings.spa_directory))
    return application


def _serve_spa(application: FastAPI, spa_directory: Path) -> None:
    application.mount(
        "/",
        StaticFiles(directory=spa_directory, html=True),
        name=SPA_MOUNT_NAME,
    )
