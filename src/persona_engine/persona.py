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
