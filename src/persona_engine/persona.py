"""The Persona record the engine returns.

A persona is a fully synthetic stand-in for a sample member: its name,
age, gender, geography and income all come from committed pools and
configured ranges, never from a real member identity.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    first_name: str
    last_name: str
    age: int
    gender: str
    geography: str
    income: int

    def to_payload(self) -> dict:
        """Return a JSON-safe payload of this persona for dataset rows."""

        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "age": self.age,
            "gender": self.gender,
            "geography": self.geography,
            "income": self.income,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "Persona":
        """Rebuild a persona from its dataset-row payload."""

        return cls(**payload)
