"""Acceptance tests for the schema migrations behind configuration storage.

AC1's saved configurations live in a persistent store, so its schema must
be created by a versioned migration, applied forward and reverted cleanly
from a clean checkout without any hand-written DDL.
"""

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

DATASET_CONFIGURATIONS_TABLE = "dataset_configurations"


def _table_names(database_path):
    import sqlite3

    connection = sqlite3.connect(str(database_path))
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        return {row[0] for row in rows}
    finally:
        connection.close()


def test_migrations_upgrade_and_downgrade_leave_the_schema_reversible(
    tmp_path, monkeypatch
):
    from alembic import command
    from alembic.config import Config

    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    scratch_database = tmp_path / "scratch.db"
    monkeypatch.setenv("APP_NAME", "fuzzy-chain-saw")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{scratch_database}")

    command.upgrade(alembic_config, "head")

    assert DATASET_CONFIGURATIONS_TABLE in _table_names(scratch_database), (
        "the applied migrations did not create the dataset_configurations table"
    )

    command.downgrade(alembic_config, "base")

    assert DATASET_CONFIGURATIONS_TABLE not in _table_names(scratch_database), (
        "the reversed migrations did not drop the dataset_configurations table"
    )
