import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings


def build_settings(spa_directory=None):
    return Settings(
        app_name="fuzzy-chain-saw",
        environment="test",
        spa_directory=spa_directory,
    )


def write_placeholder_spa(tmp_path):
    spa_directory = tmp_path / "spa"
    spa_directory.mkdir()
    (spa_directory / "index.html").write_text(
        "<!doctype html><title>Fuzzy Chain Saw</title>"
    )
    return spa_directory


def test_health_router_answers_the_healthcheck():
    client = TestClient(create_app(build_settings()))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_serves_the_built_single_page_application(tmp_path):
    client = TestClient(create_app(build_settings(write_placeholder_spa(tmp_path))))

    response = client.get("/")

    assert response.status_code == 200


def test_root_response_body_is_the_placeholder_home_page(tmp_path):
    client = TestClient(create_app(build_settings(write_placeholder_spa(tmp_path))))

    response = client.get("/")

    assert "Fuzzy Chain Saw" in response.text, (
        "The root URL must hand the browser the placeholder home page itself, "
        "not an empty 200"
    )


def test_api_health_still_answers_when_the_spa_is_mounted(tmp_path):
    client = TestClient(create_app(build_settings(write_placeholder_spa(tmp_path))))

    response = client.get("/api/health")

    assert response.status_code == 200


def test_root_without_a_built_spa_answers_not_found():
    client = TestClient(create_app(build_settings()))

    response = client.get("/")

    assert response.status_code == 404


def test_a_missing_spa_directory_fails_loudly_at_startup(tmp_path):
    never_built_directory = tmp_path / "never-built"

    with pytest.raises(RuntimeError):
        create_app(build_settings(never_built_directory))


def test_create_app_returns_a_fastapi_application():
    assert isinstance(create_app(build_settings()), FastAPI)


def test_asgi_entrypoint_resolves_configuration_from_the_environment(monkeypatch):
    monkeypatch.setenv("APP_NAME", "asgi-fuzzy-chain-saw")
    monkeypatch.setenv("ENVIRONMENT", "staging")

    asgi_reloaded = importlib.reload(importlib.import_module("app.asgi"))

    assert asgi_reloaded.app.title == "asgi-fuzzy-chain-saw"
