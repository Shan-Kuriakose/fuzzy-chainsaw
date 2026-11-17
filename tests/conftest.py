"""Structure readers shared by the pilot's test files.

The pilot's evidence lives in markdown documents. These helpers read a
document's frontmatter, section titles and tables so the pilot tests
can assert on the record's structure - which sections, tables and
required fields it carries - without asserting on its prose.

They hold no references to code under development: everything here is
plain text parsing that raises a clear message when the record is
missing or malformed.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PILOT_RECORD_PATH = REPO_ROOT / "docs" / "pilot" / "cross-persona-pilot.md"

# The personas the pilot runs its primary workflows for, in the story's
# own roster order.
WALKTHROUGH_PERSONAS = ("analyst", "developer", "bi", "qa", "privacy")


def read_pilot_record() -> str:
    """Return the pilot record text, refusing its absence loudly."""

    if not PILOT_RECORD_PATH.exists():
        raise AssertionError(
            "the pilot record must exist at docs/pilot/cross-persona-pilot.md"
        )
    return PILOT_RECORD_PATH.read_text(encoding="utf-8")


def frontmatter_of(text: str) -> str:
    """Return the YAML frontmatter block of a document."""

    frontmatter = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if frontmatter is None:
        raise AssertionError("the record must carry YAML frontmatter")
    return frontmatter.group(1)


def frontmatter_value(frontmatter: str, key: str) -> str:
    """Return the value one frontmatter key is declared with."""

    match = re.search(rf"^{key}:\s*(\S.*)$", frontmatter, re.MULTILINE)
    if match is None:
        raise AssertionError(f"frontmatter must declare {key}")
    return match.group(1).strip()


def markdown_tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    """Return every markdown table as its (header row, body rows) cells.

    Cells are lowercased; separator rows are dropped.
    """

    tables: list[tuple[list[str], list[list[str]]]] = []
    header: list[str] | None = None
    body: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip().lower() for cell in stripped.strip("|").split("|")]
            if not any(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
                if header is None:
                    header = cells
                else:
                    body.append(cells)
        elif header is not None:
            tables.append((header, body))
            header, body = None, []
    if header is not None:
        tables.append((header, body))
    return tables


def table_with_columns(
    text: str, *required_columns: str
) -> tuple[list[str], list[list[str]]]:
    """Return the document's first table carrying the required columns."""

    for header, body in markdown_tables(text):
        if all(column in header for column in required_columns):
            return header, body
    raise AssertionError(
        f"the document carries no table with the columns {required_columns}; "
        f"found {[(header, len(body)) for header, body in markdown_tables(text)]}"
    )


def section_body_of(text: str, title_fragment: str) -> str:
    """Return the body text under one section heading of a document."""

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

    for title, body in sections.items():
        if title_fragment in title:
            return body
    raise AssertionError(
        f"the document has no section titled '{title_fragment}'"
    )


def recorded_walkthrough(persona: str) -> list[str]:
    """Return the pilot record's walkthrough-outcome row for one persona.

    The row must record whether the persona's primary workflow succeeded
    or blocked, and must carry evidence of what the walkthrough
    observed - the pilot's obligation for that persona under AC1.
    """

    text = read_pilot_record()
    header, body = table_with_columns(text, "persona", "outcome", "evidence")
    persona_column = header.index("persona")
    outcome_column = header.index("outcome")
    evidence_column = header.index("evidence")

    matches = [row for row in body if persona in row[persona_column]]
    if not matches:
        raise AssertionError(
            f"the pilot record records no walkthrough outcome for the "
            f"{persona} persona"
        )
    row = matches[0]

    outcome = row[outcome_column]
    assert re.search(r"\bsuccess|\bblocker", outcome), (
        f"the {persona} persona's recorded outcome must say whether the "
        f"workflow succeeded or blocked; recorded: '{outcome}'"
    )
    assert row[evidence_column], (
        f"the {persona} persona's walkthrough outcome must carry evidence"
    )
    return row
