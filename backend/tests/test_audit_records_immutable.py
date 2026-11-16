"""Store-level refusal tests for the immutability of the audit trail.

AC2: an audit record, once written, cannot be modified or deleted by
application users - the store itself refuses UPDATE and DELETE, and
reversing the migration removes that enforcement from the schema again.
"""

import sqlite3
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]

ATLAS_TEAM = "atlas"
SAVED_NAME = "atlas-baseline"
SAVED_COUNT = 10
SAVED_SEED = 42
SAVED_CONFIGURATION = {
    "age_range": [25, 45],
    "genders": ["Female", "Male"],
    "geographies": ["Region North"],
    "income_range": [30_000, 90_000],
}

JANE_DOE = "jane.doe@example.com"

AUDIT_RECORDS_TABLE = "audit_records"
SOMEONE_ELSE = "someone-else"


def _database_path_of(tmp_path):
    return tmp_path / "configurations.db"


def _service_with_a_written_record(tmp_path):
    from app.dataset_configurations.service import DatasetConfigurationsService
    from app.settings import Settings

    settings = Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        database_url=f"sqlite:///{_database_path_of(tmp_path)}",
    )
    service = DatasetConfigurationsService.build_for(settings)
    service.save(
        ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED,
        acting_user=JANE_DOE,
    )
    return service


def _alembic_config():
    from alembic.config import Config

    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return alembic_config


def test_an_update_attempt_against_the_audit_table_is_refused_by_the_store(tmp_path):
    _service_with_a_written_record(tmp_path)
    connection = sqlite3.connect(str(_database_path_of(tmp_path)))
    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                f"UPDATE {AUDIT_RECORDS_TABLE} SET actor = ?", (SOMEONE_ELSE,)
            )
        connection.commit()
        stored_actors = connection.execute(
            f"SELECT DISTINCT actor FROM {AUDIT_RECORDS_TABLE}"
        ).fetchall()
    finally:
        connection.close()

    assert {row[0] for row in stored_actors} == {JANE_DOE}, (
        "an update rewrote an audit record through the store"
    )


def test_a_delete_attempt_against_the_audit_table_is_refused_by_the_store(tmp_path):
    _service_with_a_written_record(tmp_path)
    connection = sqlite3.connect(str(_database_path_of(tmp_path)))
    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(f"DELETE FROM {AUDIT_RECORDS_TABLE}")
        connection.commit()
        remaining = connection.execute(
            f"SELECT count(*) FROM {AUDIT_RECORDS_TABLE}"
        ).fetchone()[0]
    finally:
        connection.close()

    assert remaining > 0, "a delete removed audit records through the store"


def test_reversing_the_migration_removes_the_immutability_triggers(
    tmp_path, monkeypatch
):
    from alembic import command

    scratch_database = tmp_path / "scratch.db"
    monkeypatch.setenv("APP_NAME", "fuzzy-chain-saw")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{scratch_database}")

    command.upgrade(_alembic_config(), "head")

    trigger_names = _trigger_names_of(scratch_database)
    assert trigger_names, (
        "the applied migrations did not install the immutability triggers"
    )

    command.downgrade(_alembic_config(), "base")

    assert _trigger_names_of(scratch_database) == set(), (
        "the reversed migration left immutability triggers behind"
    )
    assert AUDIT_RECORDS_TABLE not in _table_names_of(scratch_database)


def _trigger_names_of(database_path):
    return _sqlite_master_names_of(database_path, type_="trigger")


def _table_names_of(database_path):
    return _sqlite_master_names_of(database_path, type_="table")


def _sqlite_master_names_of(database_path, type_):
    connection = sqlite3.connect(str(database_path))
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = ?", (type_,)
        ).fetchall()
        return {row[0] for row in rows}
    finally:
        connection.close()
