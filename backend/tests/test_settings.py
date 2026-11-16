import pytest


def test_settings_resolve_every_value_from_the_environment(monkeypatch):
    monkeypatch.setenv("APP_NAME", "fuzzy-chain-saw")
    monkeypatch.setenv("ENVIRONMENT", "staging")

    from app.settings import Settings

    settings = Settings()

    assert settings.app_name == "fuzzy-chain-saw"
    assert settings.environment == "staging"


def test_missing_required_setting_raises_loudly_at_startup(monkeypatch):
    from pydantic import ValidationError

    from app.settings import Settings

    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    with pytest.raises(ValidationError):
        Settings()
