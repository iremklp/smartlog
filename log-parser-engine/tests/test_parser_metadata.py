import pytest
from pydantic import ValidationError

from log_parser_engine.models import LogSourceType, ParserMetadata


def test_parser_metadata_creates_valid_model() -> None:
    metadata = ParserMetadata(
        name="iis_w3c",
        display_name="IIS W3C Log Parser",
        version="1.0.0",
        source_type=LogSourceType.iis,
        supported_extensions=("log", ".txt"),
        supported_content_types=("text/plain", "application/json"),
        tags=("iis", "w3c", "logs"),
    )

    assert metadata.identifier == "iis_w3c@1.0.0"
    assert metadata.supports_extension("LOG") is True
    assert metadata.supports_content_type("application/json; charset=utf-8") is True
    assert metadata.tags == ("iis", "w3c", "logs")


def test_parser_metadata_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        ParserMetadata(
            name="   ",
            display_name="Name",
            version="1.0.0",
            source_type=LogSourceType.iis,
        )


def test_parser_metadata_rejects_invalid_version() -> None:
    with pytest.raises(ValidationError):
        ParserMetadata(
            name="dummy",
            display_name="Dummy",
            version="1.0",
            source_type=LogSourceType.application,
        )


def test_parser_metadata_normalizes_extensions() -> None:
    metadata = ParserMetadata(
        name="json",
        display_name="JSON",
        version="1.0.0",
        source_type=LogSourceType.json,
        supported_extensions=(".json", "log", "json", "txt"),
    )

    assert metadata.supported_extensions == (".json", ".log", ".txt")


def test_parser_metadata_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ParserMetadata(
            name="dummy",
            display_name="Dummy",
            version="1.0.0",
            source_type=LogSourceType.application,
            extra_field="value",  # type: ignore[call-arg]
        )
