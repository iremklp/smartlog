from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LineEndingAnalysis:
    line_ending: str
    line_count: int
    has_trailing_newline: bool
    lf_count: int
    crlf_count: int
    cr_count: int


def analyze_line_endings(text: str) -> LineEndingAnalysis:
    lf_count = 0
    crlf_count = 0
    cr_count = 0

    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == "\r":
            if index + 1 < length and text[index + 1] == "\n":
                crlf_count += 1
                index += 2
                continue
            cr_count += 1
        elif char == "\n":
            if index == 0 or text[index - 1] != "\r":
                lf_count += 1
        index += 1

    has_trailing_newline = text.endswith(("\n", "\r"))
    line_count = len(text.splitlines())

    kinds = sum(1 for count in (lf_count, crlf_count, cr_count) if count > 0)
    if line_count == 0:
        line_ending = "none"
    elif kinds > 1:
        line_ending = "mixed"
    elif crlf_count > 0:
        line_ending = "crlf"
    elif cr_count > 0:
        line_ending = "cr"
    else:
        line_ending = "lf" if lf_count > 0 or has_trailing_newline else "none"

    return LineEndingAnalysis(
        line_ending=line_ending,
        line_count=line_count,
        has_trailing_newline=has_trailing_newline,
        lf_count=lf_count,
        crlf_count=crlf_count,
        cr_count=cr_count,
    )
