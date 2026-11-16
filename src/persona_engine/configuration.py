"""GenerationConfig: the configured demographic ranges for persona generation."""

from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class GenerationConfig:
    """The demographic ranges every generated persona is drawn from."""

    age_range: tuple[int, int] = (18, 85)
    genders: Sequence[str] = ("Female", "Male", "Non-Binary")
    geographies: Sequence[str] = (
        "Region North",
        "Region South",
        "Region East",
        "Region West",
    )
    income_range: tuple[int, int] = (20_000, 150_000)

    def __post_init__(self):
        self._validate_range("age_range", self.age_range)
        self._validate_range("income_range", self.income_range)
        self._validate_categories("genders", self.genders)
        self._validate_categories("geographies", self.geographies)

    @staticmethod
    def _validate_range(name: str, bounds: tuple[int, int]) -> None:
        low, high = bounds
        if low >= high:
            raise ValueError(
                f"{name} must be an ascending range, got ({low}, {high})"
            )
        if low < 1:
            raise ValueError(
                f"{name} lower bound must be positive, got {low}"
            )

    @staticmethod
    def _validate_categories(name: str, categories: Sequence[str]) -> None:
        if not categories:
            raise ValueError(f"{name} must contain at least one category")
        if len(set(categories)) != len(categories):
            raise ValueError(f"{name} must not contain duplicate categories")
