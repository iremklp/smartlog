import pytest
from pydantic import ValidationError

from log_parser_engine.models import DetectionCandidate, LogSourceType


def test_detection_candidate_creates_valid_model() -> None:
    candidate = DetectionCandidate(
        parser_name=" json ",
        parser_version="1.2.3",
        confidence=0.9,
        matched=True,
        priority=10,
        reason="looks right",
        signals=("json_object", "json_key"),
        source_type=LogSourceType.json,
        duration_ms=1.2,
    )

    assert candidate.parser_name == "json"
    assert candidate.identifier == "json@1.2.3"
    assert candidate.signals == ("json_object", "json_key")


def test_detection_candidate_rejects_empty_parser_name() -> None:
    with pytest.raises(ValidationError):
        DetectionCandidate(
            parser_name="   ",
            parser_version="1.0.0",
            confidence=0.8,
            matched=True,
            source_type=LogSourceType.application,
        )


def test_detection_candidate_rejects_unmatched_confidence_over_half() -> None:
    with pytest.raises(ValidationError):
        DetectionCandidate(
            parser_name="dummy",
            parser_version="1.0.0",
            confidence=0.6,
            matched=False,
            source_type=LogSourceType.application,
        )


def test_detection_candidate_rejects_error_confidence() -> None:
    with pytest.raises(ValidationError):
        DetectionCandidate(
            parser_name="dummy",
            parser_version="1.0.0",
            confidence=0.1,
            matched=False,
            source_type=LogSourceType.application,
            error="boom",
        )


def test_detection_candidate_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        DetectionCandidate(
            parser_name="dummy",
            parser_version="1.0.0",
            confidence=0.8,
            matched=True,
            source_type=LogSourceType.application,
            extra_field="value",  # type: ignore[call-arg]
        )
