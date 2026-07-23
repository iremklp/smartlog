from __future__ import annotations

from log_parser_engine.exceptions import ParserNotFoundError
from log_parser_engine.models import (
    ErrorType,
    ParseError,
    ParseResult,
    ParserRegistration,
    ParserSelection,
    ParseStatus,
)

from .detector import Detector
from .parser_context import ParserContext
from .parser_registry import ParserRegistry


class ParserManager:
    """Coordinates parser selection, parse execution, and registry state."""

    def __init__(
        self,
        registry: ParserRegistry,
        *,
        minimum_confidence: float = 0.60,
        ambiguity_margin: float = 0.05,
    ) -> None:
        if not isinstance(registry, ParserRegistry):
            raise TypeError("registry must be a ParserRegistry")
        self._registry = registry
        self._minimum_confidence = self._validate_confidence(
            minimum_confidence,
            "minimum_confidence",
        )
        self._ambiguity_margin = self._validate_confidence(
            ambiguity_margin,
            "ambiguity_margin",
        )

    @property
    def registry(self) -> ParserRegistry:
        return self._registry

    @property
    def minimum_confidence(self) -> float:
        return self._minimum_confidence

    @property
    def ambiguity_margin(self) -> float:
        return self._ambiguity_margin

    def select_parser(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> ParserSelection:
        parsers = self._registry.list_parsers(enabled_only=True)
        if not parsers:
            decision = Detector([]).detect(raw_log, context)
            return ParserSelection.from_decision(decision)

        detector = Detector(
            parsers,
            minimum_confidence=self.minimum_confidence,
            ambiguity_margin=self.ambiguity_margin,
        )
        decision = detector.detect(raw_log, context)
        return ParserSelection.from_decision(decision)

    def parse(
        self,
        raw_log: str,
        context: ParserContext | None = None,
    ) -> ParseResult:
        selection = self.select_parser(raw_log, context)
        if not selection.selected or selection.parser_name is None:
            return ParseResult(
                status=ParseStatus.failed,
                errors=[
                    ParseError(
                        message="no parser selected",
                        error_type=ErrorType.DETECTION_FAILED,
                        status=ParseStatus.failed,
                        details={"reason": selection.reason},
                    )
                ],
            )

        try:
            parser = self._registry.get(selection.parser_name)
        except ParserNotFoundError:
            return ParseResult(
                status=ParseStatus.failed,
                errors=[
                    ParseError(
                        message="selected parser disappeared from registry",
                        error_type=ErrorType.INTERNAL_ERROR,
                        status=ParseStatus.failed,
                    )
                ],
            )

        registration = self._registry.get_registration(selection.parser_name)
        if not parser.is_enabled() and not registration.enabled:
            return ParseResult(
                status=ParseStatus.failed,
                errors=[
                    ParseError(
                        message="selected parser is disabled",
                        error_type=ErrorType.INTERNAL_ERROR,
                        status=ParseStatus.failed,
                    )
                ],
            )

        try:
            return parser.safe_parse(raw_log, context)
        except Exception:  # noqa: BLE001
            return ParseResult(
                status=ParseStatus.failed,
                errors=[
                    ParseError(
                        message="parser failed during parse",
                        error_type=ErrorType.PARSE_FAILED,
                        status=ParseStatus.failed,
                    )
                ],
            )

    def parse_with(
        self,
        parser_name: str,
        raw_log: str,
        context: ParserContext | None = None,
        *,
        allow_disabled: bool = False,
    ) -> ParseResult:
        try:
            registration = self._registry.get_registration(parser_name)
        except ParserNotFoundError:
            return ParseResult(
                status=ParseStatus.failed,
                errors=[
                    ParseError(
                        message="parser not found",
                        error_type=ErrorType.INTERNAL_ERROR,
                        status=ParseStatus.failed,
                    )
                ],
            )

        if not registration.enabled and not allow_disabled:
            return ParseResult(
                status=ParseStatus.failed,
                errors=[
                    ParseError(
                        message="parser is disabled",
                        error_type=ErrorType.INTERNAL_ERROR,
                        status=ParseStatus.failed,
                    )
                ],
            )

        parser = self._registry.get(parser_name)
        try:
            return parser.safe_parse(raw_log, context)
        except Exception:  # noqa: BLE001
            return ParseResult(
                status=ParseStatus.failed,
                errors=[
                    ParseError(
                        message="parser failed during parse",
                        error_type=ErrorType.PARSE_FAILED,
                        status=ParseStatus.failed,
                    )
                ],
            )

    def available_parsers(self) -> tuple[ParserRegistration, ...]:
        return self._registry.list_registrations()

    def enabled_parsers(self) -> tuple[ParserRegistration, ...]:
        return self._registry.list_registrations(enabled_only=True)

    def _validate_confidence(self, value: float, name: str) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be between 0.0 and 1.0")
        return value
