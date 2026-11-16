"""Service-level acceptance tests for querying the audit history.

AC3: the audit history is queryable by user and by date range, the two
filters combine, and a query that matches nothing lists nothing instead
of failing.
"""

from datetime import datetime

ATLAS_TEAM = "atlas"
SAVED_NAME = "atlas-baseline"

JANE_DOE = "jane.doe@example.com"
JOHN_SMITH = "john.smith@example.com"

# Moments are UTC by the convention of this suite.
EARLY_MOMENT = datetime(2026, 11, 16, 9, 0)
MID_MOMENT = datetime(2026, 11, 16, 10, 0)
LATE_MOMENT = datetime(2026, 11, 16, 11, 0)
RANGE_LOWER_BOUND = datetime(2026, 11, 16, 9, 30)
RANGE_UPPER_BOUND = datetime(2026, 11, 16, 10, 30)


def _trail_over(tmp_path):
    from app.audit.trail import SqlAlchemyAuditTrail
    from app.storage.database import (
        apply_migrations,
        build_engine,
        build_session_factory,
    )

    database_path = tmp_path / "audit-trail.db"
    apply_migrations(f"sqlite:///{database_path}")
    engine = build_engine(f"sqlite:///{database_path}")
    return SqlAlchemyAuditTrail(build_session_factory(engine))


def _activity_of(actor, action, moment):
    from app.audit.trail import AuditedActivity

    return AuditedActivity(
        actor=actor, moment=moment, action=action, team=ATLAS_TEAM, name=SAVED_NAME
    )


def test_history_lists_records_of_the_requested_user(tmp_path):
    from app.audit.trail import DATASET_GENERATED

    trail = _trail_over(tmp_path)
    trail.append(_activity_of(JANE_DOE, DATASET_GENERATED, EARLY_MOMENT))
    trail.append(_activity_of(JOHN_SMITH, DATASET_GENERATED, EARLY_MOMENT))

    listed = trail.history(actor=JANE_DOE)

    assert [record.actor for record in listed] == [JANE_DOE]

    unrecorded = trail.history(actor="nobody-else")
    assert unrecorded == []


def test_history_lists_records_within_the_requested_date_range(tmp_path):
    from app.audit.trail import (
        DATASET_CONFIGURATION_SAVED,
        DATASET_GENERATED,
        DATASET_REPRODUCED,
    )

    trail = _trail_over(tmp_path)
    trail.append(_activity_of(JANE_DOE, DATASET_GENERATED, EARLY_MOMENT))
    trail.append(_activity_of(JANE_DOE, DATASET_CONFIGURATION_SAVED, MID_MOMENT))
    trail.append(_activity_of(JANE_DOE, DATASET_REPRODUCED, LATE_MOMENT))

    listed = trail.history(
        from_moment=RANGE_LOWER_BOUND, until_moment=RANGE_UPPER_BOUND
    )

    assert [(record.action, record.moment) for record in listed] == [
        (DATASET_CONFIGURATION_SAVED, MID_MOMENT)
    ]


def test_history_combines_the_user_and_date_range_filters(tmp_path):
    from app.audit.trail import (
        DATASET_CONFIGURATION_SAVED,
        DATASET_GENERATED,
        DATASET_REPRODUCED,
    )

    trail = _trail_over(tmp_path)
    trail.append(_activity_of(JANE_DOE, DATASET_GENERATED, EARLY_MOMENT))
    trail.append(_activity_of(JANE_DOE, DATASET_CONFIGURATION_SAVED, MID_MOMENT))
    trail.append(_activity_of(JOHN_SMITH, DATASET_CONFIGURATION_SAVED, MID_MOMENT))
    trail.append(_activity_of(JANE_DOE, DATASET_REPRODUCED, LATE_MOMENT))

    listed = trail.history(
        actor=JANE_DOE, from_moment=RANGE_LOWER_BOUND, until_moment=RANGE_UPPER_BOUND
    )

    assert [(record.actor, record.action) for record in listed] == [
        (JANE_DOE, DATASET_CONFIGURATION_SAVED)
    ]
