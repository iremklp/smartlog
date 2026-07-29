from __future__ import annotations

from collections.abc import Iterable

from log_parser_engine.core import (
    BaseParser,
    ParserContext,
    ParserManager,
    ParserRegistry,
)
from log_parser_engine.models import LogEvent


def build_parser_context(
    context: ParserContext | None,
    *,
    source_name: str | None = None,
    file_path: str | None = None,
    content_type: str | None = None,
    encoding: str = "utf-8",
) -> ParserContext:
    if context is not None:
        return context
    return ParserContext(
        source_name=source_name,
        file_path=file_path,
        content_type=content_type,
        encoding=encoding,
    )


def build_parser_registry(
    parsers: Iterable[BaseParser] | None = None,
) -> ParserRegistry:
    return ParserRegistry(parsers=parsers)


def build_parser_manager(
    registry: ParserRegistry,
    *,
    minimum_confidence: float,
    ambiguity_margin: float,
) -> ParserManager:
    return ParserManager(
        registry,
        minimum_confidence=minimum_confidence,
        ambiguity_margin=ambiguity_margin,
    )


def event_ids_from_events(events: Iterable[LogEvent]) -> tuple[str, ...]:
    return tuple(str(event.event_id) for event in events)
