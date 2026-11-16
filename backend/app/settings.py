from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration of the application, resolved exclusively from the environment.

    Every field is required unless it maps to an optional capability.
    A process started without a required value fails at startup; it never
    silently falls back to a default.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    spa_directory: Path | None = None
    database_url: str | None = None
