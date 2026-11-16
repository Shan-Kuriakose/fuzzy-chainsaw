"""Alembic environment: reads the database URL and the models' metadata.

The URL is resolved from the ``sqlalchemy.url`` option when it is set
(in-process migration runs set it programmatically) and otherwise from
the ``DATABASE_URL`` environment variable. A run without either fails
loudly; migrations never silently target a default database.
"""

import os
import sys
from pathlib import Path

from alembic import context

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.storage.models import Base  # noqa: E402

config = context.config

database_url = config.get_main_option("sqlalchemy.url") or os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "no database URL resolved for migrations: set the sqlalchemy.url "
        "option or the DATABASE_URL environment variable"
    )
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import engine_from_config, pool

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
