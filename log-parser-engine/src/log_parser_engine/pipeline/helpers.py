from __future__ import annotations

from log_parser_engine.core import BaseParser, ParserContext
from log_parser_engine.models import (
    LogEvent,
    NormalizationInput,
    ParseResult,
    PipelineOptions,
)


def extract_event_from_parse_result(parse_result: ParseResult) -> LogEvent | None:
    if parse_result.events:
        return parse_result.events[0]
    return None


def build_normalization_input_from_parse_result(
    parse_result: ParseResult,
    *,
    raw_log: str,
    parser: BaseParser,
    context: ParserContext | None,
    options: PipelineOptions,
) -> NormalizationInput | None:
    event = extract_event_from_parse_result(parse_result)
    if event is not None:
        return None
    return NormalizationInput(
        data={"message": raw_log, "raw_message": raw_log},
        source_type=parser.metadata.source_type,
        attributes={
            "parser_name": parser.name,
            "parser_version": parser.version,
            "strict_normalization": bool(options.strict_normalization),
            "preserve_unknown_fields": bool(options.preserve_unknown_fields),
            "context": {} if context is None else context.model_dump(exclude_none=True),
        },
    )
