"""Acceptance tests for the documented name-generation guarantees (AC3).

The fixed synthetic name pool and the forbidden-value screening mechanism
are part of the definition of done only if a reviewer can verify them from
the repository itself, so the README has to carry both in real words.
"""

from pathlib import Path


def test_readme_documents_fixed_pool_and_screening_mechanism():
    readme_path = (
        Path(__file__).resolve().parent.parent / "README.md"
    )
    readme = readme_path.read_text(encoding="utf-8").lower()

    assert "pool" in readme
    assert "forbidden" in readme
    assert "screen" in readme
    assert "committed" in readme
