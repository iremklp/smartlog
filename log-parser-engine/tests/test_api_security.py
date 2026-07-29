from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from log_parser_engine.api import create_app
from log_parser_engine.application import ApplicationContainer, ApplicationOptions
from log_parser_engine.core import ParserRegistry
from log_parser_engine.storage import InMemoryEventStore


def _client(options: ApplicationOptions | None = None) -> TestClient:
    resolved_options = options or ApplicationOptions(enable_builtin_parsers=False)
    container = ApplicationContainer.build(
        options=resolved_options,
        registry=ParserRegistry(),
        store=InMemoryEventStore(),
    )
    return TestClient(create_app(container=container))


@pytest.mark.parametrize(
    ("path", "expected_status"),
    (("/health", 200), ("/missing", 404), ("/docs", 200)),
)
def test_api_responses_include_security_headers(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    expected_status: int,
) -> None:
    monkeypatch.delenv("LOG_PARSER_CORS_ORIGINS", raising=False)

    response = _client().get(path)

    assert response.status_code == expected_status
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-request-id"]


def test_client_request_id_is_untrusted_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOG_PARSER_CORS_ORIGINS", raising=False)

    response = _client().get(
        "/health",
        headers={"X-Request-ID": "client-selected-id"},
    )

    request_id = response.headers["x-request-id"]
    assert request_id != "client-selected-id"
    assert re.fullmatch(r"[0-9a-f]{32}", request_id)


def test_valid_client_request_id_can_be_explicitly_trusted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOG_PARSER_CORS_ORIGINS", raising=False)
    options = ApplicationOptions(
        enable_builtin_parsers=False,
        trust_incoming_request_id=True,
    )

    response = _client(options).get(
        "/health",
        headers={"X-Request-ID": "gateway.request-42"},
    )

    assert response.headers["x-request-id"] == "gateway.request-42"


@pytest.mark.parametrize(
    "unsafe_request_id",
    ("contains/slash", "contains space", "x" * 129),
)
def test_unsafe_trusted_request_id_is_replaced(
    monkeypatch: pytest.MonkeyPatch,
    unsafe_request_id: str,
) -> None:
    monkeypatch.delenv("LOG_PARSER_CORS_ORIGINS", raising=False)
    options = ApplicationOptions(
        enable_builtin_parsers=False,
        trust_incoming_request_id=True,
    )

    response = _client(options).get(
        "/health",
        headers={"X-Request-ID": unsafe_request_id},
    )

    request_id = response.headers["x-request-id"]
    assert request_id != unsafe_request_id
    assert re.fullmatch(r"[0-9a-f]{32}", request_id)


def test_cors_preflight_uses_an_explicit_origin_method_and_header_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOG_PARSER_CORS_ORIGINS", raising=False)
    options = ApplicationOptions(
        enable_builtin_parsers=False,
        cors_allowed_origins=(
            "https://ui.example.com/",
            "https://ui.example.com",
        ),
    )

    response = _client(options).options(
        "/health",
        headers={
            "Origin": "https://ui.example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Request-ID",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "https://ui.example.com"
    )
    assert "*" not in response.headers["access-control-allow-methods"]
    assert "*" not in response.headers["access-control-allow-headers"]
    assert response.headers["x-request-id"]


def test_cors_rejects_an_origin_outside_the_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOG_PARSER_CORS_ORIGINS", raising=False)
    options = ApplicationOptions(
        enable_builtin_parsers=False,
        cors_allowed_origins=("https://ui.example.com",),
    )

    response = _client(options).options(
        "/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
    assert response.headers["x-request-id"]


def test_cors_environment_override_is_validated_and_allowlisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "LOG_PARSER_CORS_ORIGINS",
        "https://ui.example.com/, https://ops.example.com",
    )

    response = _client().options(
        "/health",
        headers={
            "Origin": "https://ops.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "https://ops.example.com"
    )


def test_cors_environment_override_rejects_wildcard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOG_PARSER_CORS_ORIGINS", "*")

    with pytest.raises(ValidationError):
        _client()


@pytest.mark.parametrize(
    "origins",
    (("*",), ("ftp://ui.example.com",), ("https://ui.example.com/path",)),
)
def test_cors_configuration_rejects_unsafe_origins(
    origins: tuple[str, ...],
) -> None:
    with pytest.raises(ValidationError):
        ApplicationOptions(cors_allowed_origins=origins)
