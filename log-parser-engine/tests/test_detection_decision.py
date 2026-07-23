import pytest
from pydantic import ValidationError

from log_parser_engine.models import (
    DetectionCandidate,
    DetectionDecision,
    LogSourceType,
)


def test_detection_decision_creates_valid_selection() -> None:
    candidate = DetectionCandidate(
        parser_name="json",
        parser_version="1.0.0",
        confidence=0.92,
        matched=True,
        source_type=LogSourceType.json,
    )
    decision = DetectionDecision(
        selected=candidate,
        candidates=(candidate,),
        minimum_confidence=0.6,
        ambiguous=False,
        reason="Parser 'json' selected with confidence 0.92.",
        duration_ms=2.5,
        evaluated_parser_count=1,
        matched_parser_count=1,
    )

    assert decision.has_match is True
    assert decision.selected_parser_name == "json"
    assert decision.top_confidence == 0.92


def test_detection_decision_rejects_invalid_selection_threshold() -> None:
    candidate = DetectionCandidate(
        parser_name="json",
        parser_version="1.0.0",
        confidence=0.5,
        matched=True,
        source_type=LogSourceType.json,
    )
    with pytest.raises(ValidationError):
        DetectionDecision(
            selected=candidate,
            candidates=(candidate,),
            minimum_confidence=0.6,
            reason="too low",
            evaluated_parser_count=1,
            matched_parser_count=1,
        )


def test_detection_decision_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        DetectionDecision(
            selected=None,
            candidates=(),
            reason="none",
            evaluated_parser_count=0,
            matched_parser_count=0,
            extra_field="value",  # type: ignore[call-arg]
        )
