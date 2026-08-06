from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from log_parser_engine.api import create_app
from log_parser_engine.application import ApplicationContainer, ApplicationOptions
from log_parser_engine.core import ParserRegistry
from log_parser_engine.storage import InMemoryEventStore


def _container() -> ApplicationContainer:
    return ApplicationContainer.build(
        options=ApplicationOptions(enable_builtin_parsers=False),
        registry=ParserRegistry([]),
        store=InMemoryEventStore(),
    )


def _write_frontend_dist(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "index.html").write_text("<html><body>ui</body></html>")
    assets = path / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "app.js").write_text("console.log('ok')")


def test_app_serves_frontend_dist_with_spa_fallback(tmp_path, monkeypatch) -> None:
    dist = tmp_path / "dist"
    _write_frontend_dist(dist)
    monkeypatch.setenv("LOG_PARSER_FRONTEND_MODE", "require")
    monkeypatch.setenv("LOG_PARSER_FRONTEND_DIST", str(dist))

    client = TestClient(create_app(container=_container()))

    index = client.get("/")
    spa = client.get("/dashboard")
    health = client.get("/api/v1/health")

    assert index.status_code == 200
    assert "ui" in index.text
    assert spa.status_code == 200
    assert "ui" in spa.text
    assert health.status_code == 200
    assert health.json()["status"] in {"healthy", "degraded"}


def test_app_frontend_api_only_mode_disables_static_mount(monkeypatch) -> None:
    monkeypatch.setenv("LOG_PARSER_FRONTEND_MODE", "api-only")
    monkeypatch.delenv("LOG_PARSER_FRONTEND_DIST", raising=False)

    client = TestClient(create_app(container=_container()))

    missing = client.get("/dashboard")
    health = client.get("/api/v1/health")

    assert missing.status_code == 404
    assert health.status_code == 200


def test_app_frontend_require_mode_fails_without_dist(monkeypatch, tmp_path) -> None:
    missing_dist = tmp_path / "missing-dist"
    monkeypatch.setenv("LOG_PARSER_FRONTEND_MODE", "require")
    monkeypatch.setenv("LOG_PARSER_FRONTEND_DIST", str(missing_dist))

    with pytest.raises(RuntimeError, match="frontend dist is required"):
        create_app(container=_container())
