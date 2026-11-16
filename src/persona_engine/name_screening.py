"""Forbidden-name screening: the last gate before emitted bytes leave.

Compliance supplies a periodically updated, non-PHI list of forbidden
values - one value per line in a plain text file - naming any value that
must never appear in an emitted dataset. A persona whose first or last
name matches a forbidden value, case-insensitively, is refused outright:
the screen never redraws, substitutes or renames, so seeded datasets
remain pure functions of seed, pools and configuration, while an updated
list that a previously saved dataset now violates fails loudly on
re-emission - the safety-correct outcome.

The compliance list carries real-identity-shaped values by design and is
never committed to this repository; the emitting call site supplies it.
"""

from dataclasses import dataclass
from pathlib import Path


class ForbiddenNameError(ValueError):
    """A persona's name matches a compliance-forbidden value."""


@dataclass(frozen=True)
class ForbiddenValueList:
    """The values compliance forbids in any emitted name component."""

    values: tuple[str, ...]

    def __post_init__(self):
        if not self.values:
            raise ValueError(
                "the compliance forbidden-value list is empty: an empty "
                "list would silently screen nothing, so its delivery is "
                "treated as a failure instead"
            )

    @classmethod
    def from_file(cls, path: Path) -> "ForbiddenValueList":
        """Load compliance's one-value-per-line text file."""

        lines = Path(path).read_text(encoding="utf-8").splitlines()
        values = tuple(line.strip() for line in lines if line.strip())
        return cls(values=values)

    def match_for(self, name_component: str) -> str | None:
        """Return the forbidden value a name component matches, if any."""

        lowered = name_component.lower()
        return next(
            (
                value
                for value in self.values
                if value.lower() == lowered
            ),
            None,
        )


def refuse_forbidden_name_components(personas, forbidden_values) -> None:
    """Raise unless every persona's name is free of forbidden components.

    Matching is exact per first/last name component, case-insensitively.
    Substring or fuzzy matching is deliberately not used: it would
    over-refuse legitimate synthetic pool names the list never meant to
    forbid.
    """

    for persona in personas:
        _refuse_forbidden_name(persona.first_name, forbidden_values)
        _refuse_forbidden_name(persona.last_name, forbidden_values)


def _refuse_forbidden_name(
    name_component: str,
    forbidden_values: ForbiddenValueList,
) -> None:
    matched = forbidden_values.match_for(name_component)
    if matched is not None:
        raise ForbiddenNameError(
            f"refusing to emit the name {name_component!r}: it matches "
            f"forbidden value {matched!r} on compliance's forbidden-value "
            "list"
        )
