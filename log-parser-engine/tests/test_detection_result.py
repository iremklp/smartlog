import pytest
from pydantic import ValidationError

from log_parser_engine.models import DetectionResult


def test_detection_result_match_and_no_match() -> None:
    matched = DetectionResult.match("dummy", 0.8, reason="header found")
    assert matched.matched is True
    assert matched.confidence == 0.8

    unmatched = DetectionResult.no_match("dummy")
    assert unmatched.matched is False
    assert unmatched.confidence == 0.0


def test_detection_result_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        DetectionResult.match("dummy", 0.0)

    with pytest.raises(ValidationError):
        DetectionResult.no_match("dummy", confidence=0.6)


def test_detection_result_normalizes_signals() -> None:
    result = DetectionResult.match(
        "dummy",
        0.9,
        signals=(" alpha ", "alpha", "beta"),
    )

    assert result.signals == ("alpha", "beta")


def test_detection_result_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        DetectionResult(
            matched=True,
            confidence=0.7,
            parser_name="dummy",
            extra_field="value",  # type: ignore[call-arg]
        )
