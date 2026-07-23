from __future__ import annotations

import time
from typing import Iterable

from log_parser_engine.exceptions import DuplicateParserError
from log_parser_engine.models import (
    DetectionCandidate,
    DetectionDecision,
    DetectionResult,
    ParserMetadata,
)

from .base_parser import BaseParser
from .parser_context import ParserContext


class Detector:
    """Selects the most suitable parser for a given log using scoring rules."""

    def __init__(
        self,
        parsers: Iterable[BaseParser],
        *,
        minimum_confidence: float = 0.60,
        ambiguity_margin: float = 0.05,
    ) -> None:
        self._parsers = self._validate_parsers(parsers)
        self._minimum_confidence = self._validate_confidence(
            minimum_confidence,
            "minimum_confidence",
        )
        self._ambiguity_margin = self._validate_confidence(
            ambiguity_margin,
            "ambiguity_margin",
        )

    @property
    def parsers(self) -> tuple[BaseParser, ...]:
        return self._parsers

    @property
    def parser_count(self) -> int:
        return len(self._parsers)

    @property
    def minimum_confidence(self) -> float:
        return self._minimum_confidence

    @property
    def ambiguity_margin(self) -> float:
        return self._ambiguity_margin

    def detect(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> DetectionDecision:
        started_at = time.perf_counter()
        enabled_parsers = self._get_enabled_parsers()
        prefiltered = self._prefilter_parsers(enabled_parsers, context)

        if not prefiltered:
            duration_ms = self._elapsed_ms(started_at)
            return DetectionDecision(
                selected=None,
                candidates=(),
                minimum_confidence=self.minimum_confidence,
                ambiguous=False,
                ambiguity_margin=self.ambiguity_margin,
                reason="No enabled parsers are registered.",
                duration_ms=duration_ms,
                evaluated_parser_count=0,
                matched_parser_count=0,
            )

        candidates: list[DetectionCandidate] = []
        for parser in prefiltered:
            candidate = self._evaluate_parser(parser, raw_log, context)
            candidates.append(candidate)

        sorted_candidates = self._sort_candidates(candidates)
        selected = self._select_candidate(sorted_candidates)
        ambiguous = self._is_ambiguous(sorted_candidates, selected)
        reason = self._build_reason(sorted_candidates, selected, ambiguous)
        duration_ms = self._elapsed_ms(started_at)

        return DetectionDecision(
            selected=selected,
            candidates=tuple(sorted_candidates),
            minimum_confidence=self.minimum_confidence,
            ambiguous=ambiguous,
            ambiguity_margin=self.ambiguity_margin,
            reason=reason,
            duration_ms=duration_ms,
            evaluated_parser_count=len(sorted_candidates),
            matched_parser_count=sum(
                1 for candidate in sorted_candidates if candidate.matched
            ),
        )

    def _validate_parsers(
        self,
        parsers: Iterable[BaseParser],
    ) -> tuple[BaseParser, ...]:
        normalized: list[BaseParser] = list(parsers)
        seen_names: set[str] = set()
        for parser in normalized:
            parser_name = parser.name.lower()
            if parser_name in seen_names:
                raise DuplicateParserError(f"duplicate parser name: {parser.name}")
            seen_names.add(parser_name)
        return tuple(normalized)

    def _validate_confidence(self, value: float, name: str) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be between 0.0 and 1.0")
        return value

    def _get_enabled_parsers(self) -> tuple[BaseParser, ...]:
        return tuple(parser for parser in self._parsers if parser.is_enabled())

    def _prefilter_parsers(
        self,
        parsers: tuple[BaseParser, ...],
        context: ParserContext | None,
    ) -> tuple[BaseParser, ...]:
        if context is None:
            return parsers

        extension_matches: list[BaseParser] = []
        content_type_matches: list[BaseParser] = []
        fallback: list[BaseParser] = []

        for parser in parsers:
            metadata = parser.metadata
            if context.file_path is not None or context.source_name is not None:
                file_hint = context.file_path or context.source_name or ""
                has_extension_match = self._matches_extension(metadata, file_hint)
                if metadata.supported_extensions and has_extension_match:
                    extension_matches.append(parser)
                    continue
                if metadata.supported_extensions and not has_extension_match:
                    continue
            if context.content_type is not None:
                content_type = context.content_type
                has_content_type_match = self._matches_content_type(
                    metadata,
                    content_type,
                )
                if metadata.supported_content_types and has_content_type_match:
                    content_type_matches.append(parser)
                    continue
                if metadata.supported_content_types and not has_content_type_match:
                    continue
            fallback.append(parser)

        if extension_matches:
            return tuple(extension_matches)
        if content_type_matches:
            return tuple(content_type_matches)
        return tuple(fallback)

    def _matches_extension(self, metadata: ParserMetadata, value: str) -> bool:
        if not value:
            return False
        if not metadata.supported_extensions:
            return True
        extension = self._extract_extension(value)
        return metadata.supports_extension(extension)

    def _matches_content_type(self, metadata: ParserMetadata, value: str) -> bool:
        if not metadata.supported_content_types:
            return True
        return metadata.supports_content_type(value)

    def _extract_extension(self, value: str) -> str:
        if "." not in value:
            return ""
        return value.rsplit(".", 1)[-1]

    def _evaluate_parser(
        self,
        parser: BaseParser,
        raw_log: str,
        context: ParserContext | None,
    ) -> DetectionCandidate:
        started_at = time.perf_counter()
        try:
            detection_result = parser.safe_detect(raw_log, context)
        except Exception as exc:  # noqa: BLE001
            detection_result = DetectionResult.no_match(
                parser.name,
                reason=f"detector wrapper failure: {type(exc).__name__}",
            )

        duration_ms = self._elapsed_ms(started_at)
        if detection_result.matched:
            return DetectionCandidate(
                parser_name=parser.name,
                parser_version=parser.version,
                confidence=detection_result.confidence,
                matched=True,
                priority=parser.metadata.priority,
                reason=detection_result.reason,
                signals=detection_result.signals,
                source_type=parser.metadata.source_type,
                duration_ms=duration_ms,
                metadata=detection_result.metadata,
            )
        error_text = self._extract_error_text(detection_result)
        if error_text is not None:
            return DetectionCandidate(
                parser_name=parser.name,
                parser_version=parser.version,
                confidence=0.0,
                matched=False,
                priority=parser.metadata.priority,
                reason=detection_result.reason,
                signals=detection_result.signals,
                source_type=parser.metadata.source_type,
                duration_ms=duration_ms,
                error=error_text,
                metadata=detection_result.metadata,
            )
        return DetectionCandidate(
            parser_name=parser.name,
            parser_version=parser.version,
            confidence=detection_result.confidence,
            matched=False,
            priority=parser.metadata.priority,
            reason=detection_result.reason,
            signals=detection_result.signals,
            source_type=parser.metadata.source_type,
            duration_ms=duration_ms,
            metadata=detection_result.metadata,
        )

    def _sort_candidates(
        self,
        candidates: Iterable[DetectionCandidate],
    ) -> tuple[DetectionCandidate, ...]:
        return tuple(
            sorted(
                candidates,
                key=self._candidate_sort_key,
            )
        )

    def _candidate_sort_key(
        self,
        candidate: DetectionCandidate,
    ) -> tuple[bool, float, int, str, str]:
        return (
            not candidate.matched,
            -candidate.confidence,
            candidate.priority,
            candidate.parser_name.lower(),
            candidate.parser_version.lower(),
        )

    def _select_candidate(
        self,
        candidates: tuple[DetectionCandidate, ...],
    ) -> DetectionCandidate | None:
        valid = tuple(
            candidate
            for candidate in candidates
            if candidate.matched and candidate.confidence >= self.minimum_confidence
        )
        if not valid:
            return None
        return valid[0]

    def _is_ambiguous(
        self,
        candidates: tuple[DetectionCandidate, ...],
        selected: DetectionCandidate | None,
    ) -> bool:
        if selected is None:
            return False
        valid = tuple(
            candidate
            for candidate in candidates
            if candidate.matched and candidate.confidence >= self.minimum_confidence
        )
        if len(valid) < 2:
            return False
        top_confidence = valid[0].confidence
        second_confidence = valid[1].confidence
        gap = top_confidence - second_confidence
        return gap <= self.ambiguity_margin

    def _build_reason(
        self,
        candidates: tuple[DetectionCandidate, ...],
        selected: DetectionCandidate | None,
        ambiguous: bool,
    ) -> str:
        if not candidates:
            return "No enabled parsers are registered."
        if selected is None:
            if any(candidate.matched for candidate in candidates):
                return "Matched parsers did not reach the minimum confidence threshold."
            return "No parser matched the input."
        if ambiguous:
            return (
                "Parser "
                f"'{selected.parser_name}' selected, but the result is ambiguous."
            )
        return (
            "Parser "
            f"'{selected.parser_name}' selected with confidence "
            f"{selected.confidence:.2f}."
        )

    def _extract_error_text(self, detection_result: DetectionResult) -> str | None:
        metadata_error = detection_result.metadata.get("error")
        if isinstance(metadata_error, str) and metadata_error:
            return metadata_error
        if hasattr(detection_result, "error"):
            error_value = getattr(detection_result, "error")
            if isinstance(error_value, str) and error_value:
                return error_value
        if (
            detection_result.reason is not None
            and "failed" in detection_result.reason.lower()
        ):
            reason_text = detection_result.reason.lower()
            if reason_text.startswith("detect failed"):
                return None
            return detection_result.reason
        return None

    def _elapsed_ms(self, started_at: float) -> float:
        elapsed = time.perf_counter() - started_at
        return max(0.0, elapsed * 1000.0)
