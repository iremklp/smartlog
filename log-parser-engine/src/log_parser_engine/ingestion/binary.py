from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class BinaryAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    is_binary_like: bool
    null_byte_count: int
    control_character_count: int
    printable_ratio: float
    sample_size: int
    signals: tuple[str, ...] = ()

    @field_validator("null_byte_count", "control_character_count", "sample_size")
    @classmethod
    def validate_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("value must not be negative")
        return value

    @field_validator("printable_ratio")
    @classmethod
    def validate_ratio(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("printable_ratio must be between 0.0 and 1.0")
        return value

    @field_validator("signals")
    @classmethod
    def normalize_signals(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            cleaned = str(item).strip().lower()
            if not cleaned or cleaned in seen:
                continue
            normalized.append(cleaned)
            seen.add(cleaned)
        return tuple(normalized)


def assess_binary_content(
    data: bytes,
    *,
    sample_size: int = 8192,
) -> BinaryAssessment:
    sample = data[:sample_size]
    null_byte_count = sample.count(b"\x00")
    control_character_count = sum(1 for byte in sample if _is_control_byte(byte))
    printable_count = sum(1 for byte in sample if _is_printable_byte(byte))
    printable_ratio = printable_count / len(sample) if sample else 1.0

    signals: list[str] = []
    if sample.startswith(
        (
            b"\x89PNG\r\n\x1a\n",
            b"%PDF",
            b"MZ",
            b"\x7fELF",
            b"PK\x03\x04",
            b"\x1f\x8b",
        )
    ):
        signals.append("known_binary_magic")
    if null_byte_count > 0:
        signals.append("null_bytes")
    if control_character_count > max(8, len(sample) // 10):
        signals.append("control_bytes")

    is_binary_like = bool(signals) and printable_ratio < 0.95
    return BinaryAssessment(
        is_binary_like=is_binary_like,
        null_byte_count=null_byte_count,
        control_character_count=control_character_count,
        printable_ratio=printable_ratio,
        sample_size=len(sample),
        signals=tuple(signals),
    )


def _is_printable_byte(byte: int) -> bool:
    return byte in {9, 10, 13} or 32 <= byte <= 126


def _is_control_byte(byte: int) -> bool:
    return byte < 32 and byte not in {9, 10, 13}
