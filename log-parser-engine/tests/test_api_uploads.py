from __future__ import annotations

import asyncio
from io import BytesIO

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from pydantic import ValidationError

from log_parser_engine.api import create_app
from log_parser_engine.api.uploads import read_bounded_upload
from log_parser_engine.application import ApplicationContainer, ApplicationOptions
from log_parser_engine.core import ParserRegistry
from log_parser_engine.exceptions import InputTooLargeError
from log_parser_engine.models import LogSourceType
from log_parser_engine.storage import InMemoryEventStore
from tests.helpers.fake_parser import FakeParser


class TrackingBytesIO(BytesIO):
    def __init__(self, value: bytes) -> None:
        super().__init__(value)
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return super().read(size)


class FailingBytesIO(TrackingBytesIO):
    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        raise OSError("simulated read failure")


def _build_client(*, max_upload_bytes: int) -> TestClient:
    parser = FakeParser(
        "fake",
        source_type=LogSourceType.FILE,
        matched=True,
        confidence=0.9,
        reason="match",
    )
    container = ApplicationContainer.build(
        options=ApplicationOptions(
            enable_builtin_parsers=False,
            max_upload_bytes=max_upload_bytes,
        ),
        registry=ParserRegistry([parser]),
        store=InMemoryEventStore(),
    )
    return TestClient(create_app(container=container))


def test_bounded_upload_uses_sized_reads_and_closes_file() -> None:
    stream = TrackingBytesIO(b"abcdef")
    upload = UploadFile(file=stream, filename="sample.log")

    payload = asyncio.run(
        read_bounded_upload(upload, max_bytes=10, chunk_size=3)
    )

    assert payload == b"abcdef"
    assert stream.read_sizes == [3, 3, 3]
    assert all(size > 0 for size in stream.read_sizes)
    assert stream.closed is True


def test_bounded_upload_stops_after_one_overflow_probe_and_closes_file() -> None:
    stream = TrackingBytesIO(b"abcdefgh")
    upload = UploadFile(file=stream, filename="sample.log")

    with pytest.raises(InputTooLargeError):
        asyncio.run(read_bounded_upload(upload, max_bytes=4, chunk_size=2))

    assert stream.read_sizes == [2, 2, 1]
    assert stream.closed is True


def test_bounded_upload_closes_file_when_read_fails() -> None:
    stream = FailingBytesIO(b"unused")
    upload = UploadFile(file=stream, filename="sample.log")

    with pytest.raises(OSError, match="simulated read failure"):
        asyncio.run(read_bounded_upload(upload, max_bytes=10))

    assert stream.closed is True


def test_bounded_upload_closes_file_when_configuration_is_invalid() -> None:
    stream = TrackingBytesIO(b"unused")
    upload = UploadFile(file=stream, filename="sample.log")

    with pytest.raises(ValueError, match="max_bytes"):
        asyncio.run(read_bounded_upload(upload, max_bytes=0))

    assert stream.read_sizes == []
    assert stream.closed is True


def test_parse_file_rejects_oversized_upload_with_safe_413_response() -> None:
    client = _build_client(max_upload_bytes=4)

    response = client.post(
        "/parse/file",
        files={"file": ("sample.log", b"abcde", "text/plain")},
    )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "input exceeds the configured size limit"
    }
    assert "abcde" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-request-id"]


def test_parse_file_accepts_an_upload_at_the_exact_limit() -> None:
    client = _build_client(max_upload_bytes=4)

    response = client.post(
        "/parse/file",
        files={"file": ("sample.log", b"test", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_parse_file_rejects_empty_upload() -> None:
    client = _build_client(max_upload_bytes=4)

    response = client.post(
        "/parse/file",
        files={"file": ("sample.log", b"", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "uploaded file is empty"}


def test_parse_file_maps_binary_ingestion_failure_without_echoing_input() -> None:
    client = _build_client(max_upload_bytes=32)
    binary_payload = b"\x00private-value\x00"

    response = client.post(
        "/parse/file",
        files={
            "file": (
                "sample.log",
                binary_payload,
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "uploaded file could not be ingested"
    }
    assert "private-value" not in response.text


def test_application_options_rejects_non_positive_upload_limit() -> None:
    with pytest.raises(ValidationError):
        ApplicationOptions(max_upload_bytes=0)
