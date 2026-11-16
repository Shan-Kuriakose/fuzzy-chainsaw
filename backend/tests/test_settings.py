import os

import pytest


def _environment_name(field_name: str) -> str:
    from app.settings import Settings

    prefix = Settings.model_config.get("env_prefix", "")
    return f"{prefix}{field_name.upper()}"


def _environment_sample_for(annotation) -> str | None:
    if annotation is bool:
        return "true"
    if annotation is int:
        return "8443"
    if annotation is float:
        return "0.5"
    if annotation is str:
        return "staging"
    return None


def test_settings_resolve_every_value_from_the_environment(monkeypatch):
    from app.settings import Settings

    environment = {}
    for field_name, field in Settings.model_fields.items():
        sample = _environment_sample_for(field.annotation)
        if sample is not None:
            environment[_environment_name(field_name)] = sample

    assert environment, "Settings declares no environment-resolvable fields"
    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    settings = Settings(_env_file=None)

    for env_name, value in environment.items():
        field_name = env_name[len(Settings.model_config.get("env_prefix", "")) :].lower()
        field = Settings.model_fields[field_name]
        assert getattr(settings, field_name) == field.annotation(value), (
            f"Setting '{field_name}' did not resolve from environment variable "
            f"'{env_name}'"
        )


def test_missing_required_setting_raises_loudly(monkeypatch):
    from pydantic import ValidationError

    from app.settings import Settings

    for field_name in Settings.model_fields:
        env_name = _environment_name(field_name)
        monkeypatch.delenv(env_name, raising=False)
        monkeypatch.delenv(os.path.basename(env_name), raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
