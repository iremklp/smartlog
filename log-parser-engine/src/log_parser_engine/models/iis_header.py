from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IisW3CHeader(BaseModel):
    """Immutable IIS W3C header metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    software: str | None = None
    version: str | None = None
    date: datetime | None = None
    fields: tuple[str, ...] = Field(default_factory=tuple)
    directives: dict[str, str] = Field(default_factory=dict)

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in value:
            cleaned = str(raw).strip().lower()
            if not cleaned:
                continue
            if cleaned in seen:
                raise ValueError("duplicate field names are not allowed")
            normalized.append(cleaned)
            seen.add(cleaned)
        return tuple(normalized)

    @field_validator("directives")
    @classmethod
    def validate_directives(cls, value: dict[str, str]) -> dict[str, str]:
        return {
            str(key).strip().lower(): str(raw_value).strip()
            for key, raw_value in value.items()
            if str(key).strip()
        }

    @field_validator("date")
    @classmethod
    def normalize_date(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @property
    def has_fields(self) -> bool:
        return bool(self.fields)

    @property
    def field_count(self) -> int:
        return len(self.fields)

    def index_of(self, field_name: str) -> int | None:
        cleaned = str(field_name).strip().lower()
        if not cleaned:
            return None
        try:
            return self.fields.index(cleaned)
        except ValueError:
            return None
