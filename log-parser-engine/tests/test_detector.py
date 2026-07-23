from __future__ import annotations

from typing import Any

import pytest

from log_parser_engine.core import BaseParser, Detector, ParserContext
from log_parser_engine.exceptions import DuplicateParserError
from log_parser_engine.models import (
    DetectionResult,
    LogSourceType,
    ParserMetadata,
)


class FakeParser(BaseParser):
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        *,
        priority: int = 100,
        enabled: bool = True,
        extensions: tuple[str, ...] = (),
        content_types: tuple[str, ...] = (),
        matched: bool = False,
        confidence: float = 0.0,
        reason: str | None = None,
        signals: tuple[str, ...] = (),
        error: str | None = None,
    ) -> None:
        super().__init__()
        self._metadata = ParserMetadata(
            name=name,
            display_name=name.replace("_", " ").title(),
            version=version,
            source_type=LogSourceType.application,
            supported_extensions=extensions,
            supported_content_types=content_types,
            priority=priority,
            enabled_by_default=enabled,
        )
        self._matched = matched
        self._confidence = confidence
        self._reason = reason
        self._signals = signals
        self._error = error

    @property
    def metadata(self) -> ParserMetadata:
        return self._metadata

    def detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionResult:
        if self._error is not None:
            raise RuntimeError(self._error)
        if self._matched:
            return DetectionResult.match(
                self.name,
                self._confidence,
                reason=self._reason,
                signals=self._signals,
            )
        return DetectionResult.no_match(
            self.name,
            confidence=self._confidence,
            reason=self._reason,
            signals=self._signals,
        )

    def parse(self, raw_log: str, context: ParserContext | None = None) -> Any:
        return None


def test_detector_allows_empty_parser_list() -> None:
    detector = Detector([])
    assert detector.parser_count == 0


def test_detector_rejects_duplicate_parser_name() -> None:
    with pytest.raises(DuplicateParserError):
        Detector([FakeParser("json"), FakeParser("JSON")])


def test_detector_rejects_invalid_confidence() -> None:
    with pytest.raises(ValueError):
        Detector([], minimum_confidence=1.2)


def test_detector_selects_matching_parser() -> None:
    parser = FakeParser("json", matched=True, confidence=0.9, reason="json")
    decision = Detector([parser]).detect("{\"message\":\"ok\"}")
    assert decision.selected is not None
    assert decision.selected.parser_name == "json"
    assert decision.selected.confidence == 0.9


def test_detector_skips_disabled_parsers() -> None:
    parser = FakeParser("json", enabled=False, matched=True, confidence=0.9)
    decision = Detector([parser]).detect("{\"message\":\"ok\"}")
    assert decision.selected is None
    assert decision.reason == "No enabled parsers are registered."


def test_detector_prefers_higher_confidence() -> None:
    low = FakeParser("json", matched=True, confidence=0.7, reason="json")
    high = FakeParser("yaml", matched=True, confidence=0.95, reason="yaml")
    decision = Detector([low, high]).detect("hello")
    assert decision.selected is not None
    assert decision.selected.parser_name == "yaml"


def test_detector_uses_priority_for_ties() -> None:
    first = FakeParser(
        "json",
        matched=True,
        confidence=0.8,
        priority=50,
        reason="json",
    )
    second = FakeParser(
        "yaml",
        matched=True,
        confidence=0.8,
        priority=10,
        reason="yaml",
    )
    decision = Detector([first, second]).detect("hello")
    assert decision.selected is not None
    assert decision.selected.parser_name == "yaml"


def test_detector_marks_ambiguity_on_close_scores() -> None:
    first = FakeParser("json", matched=True, confidence=0.80, reason="json")
    second = FakeParser("yaml", matched=True, confidence=0.79, reason="yaml")
    decision = Detector([first, second]).detect("hello")
    assert decision.ambiguous is True
    assert decision.selected is not None


def test_detector_handles_errors_without_crashing() -> None:
    parser = FakeParser("json", error="boom")
    decision = Detector([parser]).detect("hello")
    assert decision.selected is None
    assert decision.candidates[0].error == "boom"
    assert decision.candidates[0].confidence == 0.0


def test_detector_prefers_extension_matches() -> None:
    json_parser = FakeParser(
        "json",
        matched=True,
        confidence=0.9,
        reason="json",
        extensions=(".json",),
    )
    text_parser = FakeParser("text", matched=True, confidence=0.8, reason="text")
    context = ParserContext(file_path="/tmp/example.json")
    decision = Detector([json_parser, text_parser]).detect("{}", context=context)
    assert decision.selected is not None
    assert decision.selected.parser_name == "json"


def test_detector_falls_back_when_no_extension_matches() -> None:
    json_parser = FakeParser(
        "json",
        matched=True,
        confidence=0.9,
        reason="json",
        extensions=(".json",),
    )
    text_parser = FakeParser("text", matched=True, confidence=0.8, reason="text")
    context = ParserContext(file_path="/tmp/example.log")
    decision = Detector([json_parser, text_parser]).detect("{}", context=context)
    assert decision.selected is not None
    assert decision.selected.parser_name == "text"


def test_detector_uses_content_type_filter() -> None:
    json_parser = FakeParser(
        "json",
        matched=True,
        confidence=0.9,
        reason="json",
        content_types=("application/json",),
    )
    text_parser = FakeParser("text", matched=True, confidence=0.8, reason="text")
    context = ParserContext(content_type="application/json")
    decision = Detector([json_parser, text_parser]).detect("{}", context=context)
    assert decision.selected is not None
    assert decision.selected.parser_name == "json"


def test_detector_reports_counts_and_duration() -> None:
    parser = FakeParser("json", matched=True, confidence=0.9, reason="json")
    decision = Detector([parser]).detect("hello")
    assert decision.evaluated_parser_count == 1
    assert decision.matched_parser_count == 1
    assert decision.duration_ms >= 0.0
