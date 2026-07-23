from __future__ import annotations

import pytest
from pydantic import ValidationError

from log_parser_engine.models import (
    DetectionCandidate,
    DetectionDecision,
    LogSourceType,
    ParserSelection,
)


def test_parser_selection_creates_valid_selection() -> None:
    decision = DetectionDecision(
        selected=DetectionCandidate(
            parser_name="json",
            parser_version="1.0.0",
            confidence=0.9,
            matched=True,
            priority=100,
            reason="ok",
            source_type=LogSourceType.JSON,
        ),
        candidates=(
            DetectionCandidate(
                parser_name="json",
                parser_version="1.0.0",
                confidence=0.9,
                matched=True,
                priority=100,
                reason="ok",
                source_type=LogSourceType.JSON,
            ),
        ),
        reason="ok",
        evaluated_parser_count=1,
        matched_parser_count=1,
    )
    selection = ParserSelection.from_decision(decision)
    assert selection.selected is True
    assert selection.identifier == "json@1.0.0"
    assert selection.confidence == 0.9
    assert selection.source_type == LogSourceType.JSON


def test_parser_selection_creates_unselected_result() -> None:
    decision = DetectionDecision(
        selected=None,
        candidates=(),
        reason="no match",
        evaluated_parser_count=0,
        matched_parser_count=0,
    )
    selection = ParserSelection.from_decision(decision)
    assert selection.selected is False
    assert selection.parser_name is None
    assert selection.parser_version is None
    assert selection.source_type is None
    assert selection.confidence is None
    assert selection.ambiguous is False


def test_parser_selection_rejects_invalid_state() -> None:
    decision = DetectionDecision(
        selected=None,
        candidates=(),
        reason="no match",
        evaluated_parser_count=0,
        matched_parser_count=0,
    )
    with pytest.raises(ValueError):
        ParserSelection(
            parser_name=None,
            parser_version="1.0.0",
            source_type=None,
            confidence=None,
            ambiguous=False,
            reason="no match",
            decision=decision,
        )


def test_parser_selection_rejects_empty_reason() -> None:
    decision = DetectionDecision(
        selected=None,
        candidates=(),
        reason="no match",
        evaluated_parser_count=0,
        matched_parser_count=0,
    )
    with pytest.raises(ValidationError):
        ParserSelection(
            parser_name=None,
            parser_version=None,
            source_type=None,
            confidence=None,
            ambiguous=False,
            reason="   ",
            decision=decision,
        )


def test_parser_selection_rejects_extra_fields() -> None:
    decision = DetectionDecision(
        selected=None,
        candidates=(),
        reason="no match",
        evaluated_parser_count=0,
        matched_parser_count=0,
    )
    with pytest.raises(ValidationError):
        ParserSelection(
            parser_name=None,
            parser_version=None,
            source_type=None,
            confidence=None,
            ambiguous=False,
            reason="no match",
            decision=decision,
            extra=1,  # type: ignore[call-arg]
        )
