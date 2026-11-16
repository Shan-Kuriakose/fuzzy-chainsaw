"""Acceptance tests for the privacy-review documentation packet.

Each test maps to an acceptance criterion of the story:
AC1 - the packet explains the generation method, attribute sources,
      safeguards and monitoring controls
AC2 - the packet states explicit never-contains criteria, and its
      permitted-field list cannot drift from the Persona record
AC3 - the packet is versioned and carries an approval record completed
      at sign-off
"""

import dataclasses
import re
from pathlib import Path

PACKET_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "privacy"
    / "generation-approach.md"
)


def _packet_text() -> str | None:
    if not PACKET_PATH.exists():
        return None
    return PACKET_PATH.read_text(encoding="utf-8")


def _sections(text: str) -> dict[str, str]:
    """Map each markdown heading (lowercased) to the body text under it."""

    sections: dict[str, str] = {}
    current_title = "(preamble)"
    body_lines: list[str] = []
    for line in text.splitlines():
        heading = re.match(r"^#{1,6}\s+(.*)$", line)
        if heading:
            sections[current_title] = "\n".join(body_lines)
            current_title = heading.group(1).strip().lower()
            body_lines = []
        else:
            body_lines.append(line)
    sections[current_title] = "\n".join(body_lines)
    return sections


def _section_body(sections: dict[str, str], title_fragment: str) -> str:
    for title, body in sections.items():
        if title_fragment in title:
            return body
    raise AssertionError(f"the packet has no section titled '{title_fragment}'")


def _fenced_code_blocks(text: str) -> list[str]:
    blocks = re.findall(r"```[^\n]*\n(.*?)```", text, re.DOTALL)
    return blocks


def _table_header_rows(text: str) -> list[list[str]]:
    headers: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip().lower() for cell in stripped.strip("|").split("|")]
            headers.append(cells)
    return headers


def test_required_sections_present():
    text = _packet_text()
    assert text is not None, (
        "the packet must exist at docs/privacy/generation-approach.md"
    )
    sections = _sections(text)

    generation = _section_body(sections, "generation method")
    assert "random.Random" in generation, (
        "the generation method must name the seeded random.Random source"
    )
    assert re.search(r"\bseeded?\b", generation, re.IGNORECASE), (
        "the generation method must say the source is seeded"
    )
    assert re.search(r"consumption order", generation, re.IGNORECASE), (
        "the generation method must state the fixed attribute consumption order"
    )

    sources = _section_body(sections, "attribute sources").lower()
    for expected in ("name", "pool", "age", "income", "gender", "geograph"):
        assert expected in sources, (
            f"attribute sources must cover '{expected}'"
        )

    safeguards = _section_body(sections, "safeguards").lower()
    assert "provenance" in safeguards, (
        "safeguards must mention the frozen configuration recorded as provenance"
    )
    assert "validat" in safeguards, (
        "safeguards must mention validated ranges and categories"
    )
    assert re.search(r"refus|422", safeguards), (
        "safeguards must mention bounds that refuse loudly"
    )

    monitoring = _section_body(sections, "monitoring")
    monitoring_lower = monitoring.lower()
    for expected in ("manifest", "replay"):
        assert expected in monitoring_lower, (
            f"monitoring controls must cover '{expected}'"
        )
    assert re.search(r"\bCI\b|continuous integration", monitoring), (
        "monitoring controls must cover CI enforcement"
    )
    assert re.search(r"deferred|not (yet|currently)|future work|out of scope", monitoring_lower), (
        "monitoring controls must state explicitly that production "
        "monitoring is deferred, not claimed as an existing control"
    )


def test_never_contains_criteria_are_explicit():
    text = _packet_text()
    assert text is not None, (
        "the packet must exist at docs/privacy/generation-approach.md"
    )
    never_body = _section_body(_sections(text), "never").lower()

    for field in ("first_name", "last_name", "age", "gender", "geography", "income"):
        assert field in never_body, (
            f"the never-contains section must enumerate the permitted "
            f"field '{field}'"
        )

    assert "synthetic" in never_body, (
        "the guarantee must be worded as values drawn from synthetic sources"
    )
    assert "real" in never_body and "member" in never_body, (
        "the never-contains section must prohibit anything sourced from "
        "real member data"
    )


def test_permitted_fields_match_the_persona_record():
    text = _packet_text()
    assert text is not None, (
        "the packet must exist at docs/privacy/generation-approach.md"
    )

    from persona_engine.persona import Persona

    expected = tuple(field.name for field in dataclasses.fields(Persona))

    field_blocks = []
    for block in _fenced_code_blocks(text):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines and all(re.fullmatch(r"[a-z][a-z0-9_]*", line) for line in lines):
            field_blocks.append(lines)

    assert len(field_blocks) == 1, (
        "the packet must list the permitted fields as exactly one fenced "
        "block of field names, one per line"
    )
    assert tuple(field_blocks[0]) == expected, (
        "the packet's permitted-field list must equal the Persona record's "
        "fields, so the packet cannot silently drift from the code it "
        "certifies"
    )


def test_document_is_versioned_with_approval_record():
    text = _packet_text()
    assert text is not None, (
        "the packet must exist at docs/privacy/generation-approach.md"
    )

    frontmatter = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    assert frontmatter is not None, "the packet must carry YAML frontmatter"
    frontmatter_text = frontmatter.group(1)

    version_match = re.search(r"^document_version:\s*(\S+)", frontmatter_text, re.MULTILINE)
    assert version_match is not None, (
        "frontmatter must declare document_version"
    )
    assert re.search(r"^status:\s*\S+", frontmatter_text, re.MULTILINE), (
        "frontmatter must declare status"
    )

    version = version_match.group(1)
    body_after_frontmatter = text[frontmatter.end():]
    assert version in body_after_frontmatter, (
        "the revision history must reference the current document_version"
    )

    headers = _table_header_rows(text)
    approval_rows = [
        row
        for row in headers
        if {"approver", "role", "decision", "rationale", "date"} <= set(row)
    ]
    assert approval_rows, (
        "the packet must carry an approval-record table with approver, "
        "role, decision, rationale and date columns"
    )

    history_rows = [
        row
        for row in headers
        if ("version" in row or "revision" in row) and "date" in row
    ]
    assert history_rows, (
        "the packet must carry a revision-history table with a version "
        "and date"
    )
