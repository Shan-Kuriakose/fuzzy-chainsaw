"""Database connections and schema for persisted application state.

The engine is built from the settings' database URL; the schema itself is
created exclusively by applying the versioned migrations, never by raw
DDL at startup.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_REVISION = "head"

DatabaseSession = sessionmaker[Session]


def build_engine(database_url: str | None) -> Engine:
    """Build the database engine, refusing to invent a database."""

    if not database_url:
        raise RuntimeError(
            "no database_url is configured; dataset configuration storage "
            "is unavailable"
        )
    return create_engine(database_url)


def apply_migrations(database_url: str) -> None:
    """Bring the database schema up to head through the versioned migrations."""

    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, MIGRATIONS_REVISION)


def build_session_factory(engine: Engine) -> DatabaseSession:
    """Build the session factory the repository opens a unit of work with."""

    return sessionmaker(bind=engine, expire_on_commit=False)
