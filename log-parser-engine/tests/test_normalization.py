from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from log_parser_engine.exceptions import NormalizationError
from log_parser_engine.models import (
    LogEvent,
    LogSeverity,
    LogSourceType,
    NormalizationInput,
    NormalizationResult,
    NormalizationWarning,
)
from log_parser_engine.normalization import (
    Normalizer,
    build_field_mapping,
    normalize_duration,
    normalize_severity,
    normalize_timestamp,
)


def test_normalization_input_supports_mapping_input() -> None:
    payload = NormalizationInput(data={"message": "hello"}, source_type="nginx")

    assert payload.data["message"] == "hello"
    assert payload.source_type == "nginx"


def test_normalization_models_validate_messages() -> None:
    with pytest.raises(ValidationError):
        NormalizationWarning(message="   ")

    result = NormalizationResult(
        event=LogEvent(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            source_type=LogSourceType.application,
            message="ok",
            raw_message="ok",
        ),
        warnings=[NormalizationWarning(message="bad")],
    )

    assert result.warnings[0].message == "bad"


def test_normalize_timestamp_and_severity_helpers() -> None:
    dt = normalize_timestamp("2024-01-01T12:00:00Z")
    assert dt.tzinfo is not None

    assert normalize_severity("error") == LogSeverity.error
    assert normalize_severity("WARN") == LogSeverity.warning

    assert normalize_duration("12.5") == 12.5

    with pytest.raises(NormalizationError):
        normalize_timestamp("not-a-date")


def test_normalizer_builds_log_event_from_mapped_payload() -> None:
    mapping = build_field_mapping(
        {
            "message": "msg",
            "timestamp": "ts",
            "severity": "sev",
            "duration_ms": "duration",
            "source_type": "source",
        }
    )
    normalizer = Normalizer(field_mapping=mapping)

    result = normalizer.normalize(
        {
            "msg": "hello world",
            "ts": "2024-01-01T12:30:00+00:00",
            "sev": "warning",
            "duration": "4.25",
            "source": "nginx",
        }
    )

    assert isinstance(result, NormalizationResult)
    assert isinstance(result.event, LogEvent)
    assert result.event.message == "hello world"
    assert result.event.severity == LogSeverity.warning
    assert result.event.duration_ms == 4.25
    assert result.event.source_type == LogSourceType.nginx
    assert result.warnings == []
