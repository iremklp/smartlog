from __future__ import annotations

from datetime import timezone

import pytest
from pydantic import ValidationError

from log_parser_engine.models import (
    LogSourceType,
    ParserMetadata,
    ParserRegistration,
)


def test_parser_registration_creates_valid_registration() -> None:
    metadata = ParserMetadata(
        name="iis",
        display_name="IIS Parser",
        version="1.0.0",
        source_type=LogSourceType.IIS,
    )
    registration = ParserRegistration(
        parser_name="iis",
        parser_version="1.0.0",
        source_type=LogSourceType.IIS,
        metadata=metadata,
        registration_order=1,
    )
    assert registration.identifier == "iis@1.0.0"
    assert registration.enabled is True
    assert registration.origin is None
    assert registration.notes is None
    assert registration.registered_at.tzinfo is not None
    assert registration.registered_at.astimezone(timezone.utc).tzinfo is not None


def test_parser_registration_trims_and_normalizes_values() -> None:
    metadata = ParserMetadata(
        name=" Redis ",
        display_name="Redis Parser",
        version=" 1.2.3 ",
        source_type=LogSourceType.REDIS,
    )
    registration = ParserRegistration(
        parser_name=" Redis ",
        parser_version=" 1.2.3 ",
        source_type=LogSourceType.REDIS,
        metadata=metadata,
        registration_order=2,
        origin="  PLUGIN  ",
        notes="  ok  ",
    )
    assert registration.parser_name == "Redis"
    assert registration.parser_version == "1.2.3"
    assert registration.origin == "plugin"
    assert registration.notes == "ok"


def test_parser_registration_rejects_negative_registration_order() -> None:
    metadata = ParserMetadata(
        name="json",
        display_name="Json Parser",
        version="1.0.0",
        source_type=LogSourceType.JSON,
    )
    with pytest.raises(ValidationError):
        ParserRegistration(
            parser_name="json",
            parser_version="1.0.0",
            source_type=LogSourceType.JSON,
            metadata=metadata,
            registration_order=-1,
        )


def test_parser_registration_rejects_mismatched_name() -> None:
    metadata = ParserMetadata(
        name="json",
        display_name="Json Parser",
        version="1.0.0",
        source_type=LogSourceType.JSON,
    )
    with pytest.raises(ValueError):
        ParserRegistration(
            parser_name="xml",
            parser_version="1.0.0",
            source_type=LogSourceType.JSON,
            metadata=metadata,
            registration_order=1,
        )


def test_parser_registration_rejects_mismatched_version() -> None:
    metadata = ParserMetadata(
        name="json",
        display_name="Json Parser",
        version="1.0.0",
        source_type=LogSourceType.JSON,
    )
    with pytest.raises(ValueError):
        ParserRegistration(
            parser_name="json",
            parser_version="2.0.0",
            source_type=LogSourceType.JSON,
            metadata=metadata,
            registration_order=1,
        )


def test_parser_registration_rejects_mismatched_source_type() -> None:
    metadata = ParserMetadata(
        name="json",
        display_name="Json Parser",
        version="1.0.0",
        source_type=LogSourceType.JSON,
    )
    with pytest.raises(ValueError):
        ParserRegistration(
            parser_name="json",
            parser_version="1.0.0",
            source_type=LogSourceType.XML,
            metadata=metadata,
            registration_order=1,
        )


def test_parser_registration_is_immutable() -> None:
    metadata = ParserMetadata(
        name="json",
        display_name="Json Parser",
        version="1.0.0",
        source_type=LogSourceType.JSON,
    )
    registration = ParserRegistration(
        parser_name="json",
        parser_version="1.0.0",
        source_type=LogSourceType.JSON,
        metadata=metadata,
        registration_order=1,
    )
    with pytest.raises(ValidationError):
        registration.enabled = False  # type: ignore[misc]


def test_parser_registration_rejects_extra_fields() -> None:
    metadata = ParserMetadata(
        name="json",
        display_name="Json Parser",
        version="1.0.0",
        source_type=LogSourceType.JSON,
    )
    with pytest.raises(ValidationError):
        ParserRegistration(
            parser_name="json",
            parser_version="1.0.0",
            source_type=LogSourceType.JSON,
            metadata=metadata,
            registration_order=1,
            extra=1,  # type: ignore[call-arg]
        )
