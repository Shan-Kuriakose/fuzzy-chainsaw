"""Service-level acceptance tests for the audit trail of generation activity.

AC1: every generation and configuration change leaves an audit record
naming the user who acted, the moment, the action and the configuration
it concerned - written alongside the activity itself, so a save and its
records survive or refuse together.
"""

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
JOHN_SMITH = "john.smith@example.com"


def _service_over(tmp_path):
    from app.dataset_configurations.service import DatasetConfigurationsService
    from app.settings import Settings

    settings = Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'configurations.db'}",
    )
    return DatasetConfigurationsService.build_for(settings)


def _written_records(tmp_path):
    from app.audit.trail import SqlAlchemyAuditTrail
    from app.storage.database import build_engine, build_session_factory

    engine = build_engine(f"sqlite:///{tmp_path / 'configurations.db'}")
    trail = SqlAlchemyAuditTrail(build_session_factory(engine))
    return trail.history()


def _save_the_saved_configuration_by(service, acting_user):
    service.save(
        ATLAS_TEAM,
        SAVED_NAME,
        SAVED_CONFIGURATION,
        SAVED_COUNT,
        SAVED_SEED,
        acting_user=acting_user,
    )


def test_a_save_writes_separate_records_for_the_generation_and_the_configuration_change(
    tmp_path,
):
    from app.audit.trail import DATASET_CONFIGURATION_SAVED, DATASET_GENERATED

    service = _service_over(tmp_path)

    _save_the_saved_configuration_by(service, JANE_DOE)

    records = _written_records(tmp_path)
    assert {record.action for record in records} == {
        DATASET_GENERATED,
        DATASET_CONFIGURATION_SAVED,
    }, "one action of the save is missing its audit record"
    assert len(records) == 2, "actions of one save must not collapse into one record"
    for record in records:
        assert record.actor == JANE_DOE
        assert record.team == ATLAS_TEAM
        assert record.name == SAVED_NAME
        assert record.moment is not None


def test_a_reproduce_writes_a_record_with_the_actor_and_the_configuration_reference(
    tmp_path,
):
    from app.audit.trail import DATASET_REPRODUCED

    service = _service_over(tmp_path)
    _save_the_saved_configuration_by(service, JANE_DOE)

    service.reproduce(ATLAS_TEAM, SAVED_NAME, acting_user=JOHN_SMITH)

    reproduced = [
        record
        for record in _written_records(tmp_path)
        if record.action == DATASET_REPRODUCED
    ]
    assert len(reproduced) == 1
    assert reproduced[0].actor == JOHN_SMITH
    assert reproduced[0].team == ATLAS_TEAM
    assert reproduced[0].name == SAVED_NAME


def test_a_save_without_request_identity_is_recorded_as_unauthenticated(tmp_path):
    from app.audit.trail import UNAUTHENTICATED_ACTOR

    service = _service_over(tmp_path)

    service.save(ATLAS_TEAM, SAVED_NAME, SAVED_CONFIGURATION, SAVED_COUNT, SAVED_SEED)

    records = _written_records(tmp_path)
    assert {record.actor for record in records} == {UNAUTHENTICATED_ACTOR}
