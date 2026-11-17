"""Structural acceptance tests for the pilot's written record.

The record lives at docs/pilot/cross-persona-pilot.md and is the
evidence home for the pilot's acceptance criteria. These tests hold
the record to the story's requirements: what it must declare about
itself, which walkthrough outcomes it must carry, how it triages
findings, and what its go-live checklist must confirm. They assert
structure -- sections, table shape, required fields -- never specific
prose, mirroring the precedent of tests/test_privacy_documentation.py.

Each test maps to the story's acceptance criteria:
AC1 - the record declares its own state and records every persona's
      success or blockers with evidence
AC2 - every pilot finding is triaged blocking (fixed with a regression
      test) or non-blocking (logged for the post-launch backlog)
AC3 - the go-live criteria, including the privacy sign-off, are
      confirmed as met with evidence
"""

import re

from conftest import (
    WALKTHROUGH_PERSONAS,
    frontmatter_of,
    frontmatter_value,
    read_pilot_record,
    recorded_walkthrough,
    section_body_of,
    table_with_columns,
)


def test_success_and_blockers_recorded_per_persona():
    text = read_pilot_record()
    frontmatter = frontmatter_of(text)
    frontmatter_value(frontmatter, "document_version")
    status = frontmatter_value(frontmatter, "status")
    assert status, "the record's frontmatter must declare its status"

    for persona in WALKTHROUGH_PERSONAS:
        recorded_walkthrough(persona)


def test_every_finding_is_triaged_blocking_or_backlogged():
    text = read_pilot_record()

    section_body_of(text, "backlog")

    header, rows = table_with_columns(text, "finding", "triage", "regression test")
    assert rows, "the record must carry its triaged findings as rows"

    findings_column = header.index("finding")
    triage_column = header.index("triage")
    regression_column = header.index("regression test")

    authentication_rows = []
    for row in rows:
        finding = row[findings_column]
        triage = row[triage_column]
        backlogged = re.search(r"non.?blocking|\bbacklog", triage) is not None
        assert backlogged or "blocking" in triage, (
            f"finding '{finding}' must be triaged as blocking or logged "
            f"to the post-launch backlog; recorded: '{triage}'"
        )
        if not backlogged:
            assert row[regression_column], (
                f"blocking finding '{finding}' must name its regression test"
            )
        if "auth" in finding:
            authentication_rows.append((row, backlogged))

    assert authentication_rows, (
        "the record must triage the finding that the backend exposes no "
        "authentication, so its documented deferral is a recorded "
        "decision rather than an omission"
    )
    assert all(backlogged for _, backlogged in authentication_rows), (
        "the no-authentication finding must be triaged non-blocking "
        "against the documented deferral; real leakage or loss is what "
        "trips blocking"
    )


def test_go_live_criteria_confirmed_with_evidence():
    text = read_pilot_record()

    header, rows = table_with_columns(text, "criterion", "evidence", "status")
    assert rows, "the record must carry the go-live criteria as rows"

    criterion_column = header.index("criterion")
    evidence_column = header.index("evidence")
    status_column = header.index("status")

    privacy_rows = []
    for row in rows:
        assert row[evidence_column], (
            f"go-live criterion '{row[criterion_column]}' must carry "
            "evidence that it is met"
        )
        assert re.search(r"confirm|met|pass", row[status_column]), (
            f"go-live criterion '{row[criterion_column]}' must be "
            f"confirmed as met; recorded: '{row[status_column]}'"
        )
        if "privacy" in " ".join(row):
            privacy_rows.append(row)

    assert privacy_rows, (
        "the go-live criteria must include the privacy sign-off"
    )
    assert all(
        re.search(r"generation-approach|docs/privacy", row[evidence_column])
        for row in privacy_rows
    ), (
        "the privacy sign-off criterion must cite the generation "
        "approach packet as its evidence"
    )
