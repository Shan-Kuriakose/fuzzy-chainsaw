"""Acceptance tests for the privacy-review documentation packet."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[2]
DOCUMENT_PATH = (
    REPOSITORY_ROOT
    / "docs"
    / "privacy"
    / "synthetic-data-generation.md"
)


def _document_text() -> str:
    return DOCUMENT_PATH.read_text(encoding="utf-8")


def test_local_random_generation_uses_fixed_pools_and_configured_partitions():
    document = _document_text()

    assert "## Generation Method" in document
    assert "seeded local random" in document.lower()
    assert "fixed synthetic name pool" in document.lower()
    assert "fixed synthetic geography pool" in document.lower()
    assert "configured demographic range" in document.lower()
    assert "configured income range" in document.lower()
    assert "no external network" in document.lower()


def test_provenance_records_immutable_generation_sources():
    document = _document_text()

    assert "## Provenance" in document
    assert "immutable" in document.lower()
    assert "generation seed" in document.lower()
    assert "generation configuration" in document.lower()
    assert "synthetic name and geography pools" in document.lower()


def test_archive_permissions_match_repository_review_controls():
    document = _document_text()

    assert "## Archive Permissions" in document
    assert "review-controlled" in document.lower()
    assert "world-readable" in document.lower()
    assert "owners and reviewers" in document.lower()


def test_signoff_launch_activates_public_dataset_availability():
    document = _document_text()

    assert "## Launch Checklist" in document
    assert "approved sign-off" in document.lower()
    assert "public dataset availability" in document.lower()
    assert "only after" in document.lower()


def test_never_contain_rules_exclude_direct_and_quasi_identifiers():
    document = _document_text()

    assert "## Never Contain" in document
    for identifier in (
        "names",
        "national identifiers",
        "health-plan member identifiers",
        "provider identifiers",
        "account numbers",
        "device numbers",
        "record numbers",
        "dates narrower than a year",
        "geography smaller than a state",
        "contact details",
        "health conditions",
        "procedures",
    ):
        assert identifier in document.lower()


def test_output_schema_confines_values_to_available_source_fields():
    document = _document_text()

    assert "## Output Schema" in document
    for required_field in (
        "first_name",
        "last_name",
        "age",
        "gender",
        "geography",
        "income",
    ):
        assert required_field in document.lower()

    assert "fields outside this schema" in document.lower()
    assert "free-text output" in document.lower()


def test_launch_gateway_requires_approved_monitoring_and_schema_records():
    document = _document_text()

    assert "## Launch Checklist" in document
    assert "approved monitoring controls" in document.lower()
    assert "reviewed output schema" in document.lower()
    assert "never-contain criteria" in document.lower()


def test_launch_gateway_preserves_monitoring_baseline_in_reviewed_artifact():
    document = _document_text()

    assert "## Monitoring Controls" in document
    assert "automated provenance and replay verification" in document.lower()
    assert "No runtime PHI detection" in document
    assert "no other runtime monitoring is claimed" in document.lower()
    assert "baseline remains unchanged" in document.lower()
    assert "## Spanish Sign-off Summary" in document
    assert "monitoring conclusion" in document.lower()
    assert "preserve" in document.lower()
