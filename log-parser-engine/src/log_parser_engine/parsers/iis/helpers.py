from __future__ import annotations

from log_parser_engine.core.parser_context import ParserContext
from log_parser_engine.models.iis_header import IisW3CHeader

from .header import parse_iis_fields


def resolve_fields(
    raw_log: str,
    header: IisW3CHeader | None,
    context: ParserContext | None,
) -> tuple[str, ...]:
    if header is not None and header.has_fields:
        return header.fields
    if context is not None and context.attributes.get("iis_fields"):
        raw_fields = context.attributes["iis_fields"]
        if isinstance(raw_fields, str):
            return parse_iis_fields(raw_fields)
        if isinstance(raw_fields, (tuple, list)):
            return parse_iis_fields(" ".join(str(item) for item in raw_fields))
    if context is not None and context.attributes.get("fields"):
        raw_fields = context.attributes["fields"]
        if isinstance(raw_fields, str):
            return parse_iis_fields(raw_fields)
        if isinstance(raw_fields, (tuple, list)):
            return parse_iis_fields(" ".join(str(item) for item in raw_fields))
    raise ValueError("no IIS field list available")


def select_first_data_record(
    raw_log: str,
) -> tuple[IisW3CHeader, str, int, tuple[str, ...]]:
    lines = [line.rstrip("\n") for line in raw_log.splitlines()]
    header_lines: list[str] = []
    data_lines: list[str] = []
    header: IisW3CHeader | None = None
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            header_lines.append(line)
            continue
        data_lines.append(line)
        if header is None:
            header = _build_header(header_lines)
        break

    if header is None:
        header = _build_header(header_lines)

    if not data_lines:
        raise ValueError("no data lines found")

    selected = data_lines[0]
    return header, selected, 1, tuple(data_lines[1:])


def _build_header(header_lines: list[str]) -> IisW3CHeader:
    from .header import parse_iis_header

    return parse_iis_header(header_lines)
