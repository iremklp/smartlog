from __future__ import annotations

from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ParserRecordStrategy(BaseModel):
    """Parser-specific record handling strategy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    parser_name: str
    mode: Literal["line", "document", "stateful_line"]
    header_prefixes: tuple[str, ...] = Field(default_factory=tuple)
    comment_prefixes: tuple[str, ...] = Field(default_factory=tuple)
    supports_state: bool = False

    @field_validator("parser_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("parser_name must not be empty")
        return cleaned

    @field_validator("header_prefixes", "comment_prefixes")
    @classmethod
    def normalize_prefixes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for prefix in value:
            cleaned = str(prefix)
            if cleaned:
                normalized.append(cleaned)
        return tuple(normalized)


DEFAULT_PARSER_STRATEGIES: dict[str, ParserRecordStrategy] = {
    "iis_w3c": ParserRecordStrategy(
        parser_name="iis_w3c",
        mode="stateful_line",
        header_prefixes=("#",),
        comment_prefixes=("#",),
        supports_state=True,
    ),
    "redis_log": ParserRecordStrategy(parser_name="redis_log", mode="line"),
    "json_log": ParserRecordStrategy(parser_name="json_log", mode="line"),
    "apache_nginx_access": ParserRecordStrategy(
        parser_name="apache_nginx_access",
        mode="line",
    ),
    "apache_nginx_error": ParserRecordStrategy(
        parser_name="apache_nginx_error",
        mode="line",
    ),
    "windows_event_xml": ParserRecordStrategy(
        parser_name="windows_event_xml",
        mode="document",
    ),
    "syslog_rfc5424": ParserRecordStrategy(parser_name="syslog_rfc5424", mode="line"),
    "syslog_rfc3164": ParserRecordStrategy(parser_name="syslog_rfc3164", mode="line"),
}


def build_strategy_map(
    custom: Mapping[str, ParserRecordStrategy] | None,
) -> dict[str, ParserRecordStrategy]:
    strategies = dict(DEFAULT_PARSER_STRATEGIES)
    if custom is None:
        return strategies
    for key, value in custom.items():
        normalized_key = key.strip().lower()
        if not normalized_key:
            raise ValueError("strategy key must not be empty")
        if value.parser_name != normalized_key:
            value = value.model_copy(update={"parser_name": normalized_key})
        strategies[normalized_key] = value
    return strategies
