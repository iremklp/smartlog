from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import LogSourceType


class ParserMetadata(BaseModel):
    """Immutable metadata describing a parser contract and capabilities."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    display_name: str
    version: str
    source_type: LogSourceType
    description: str | None = None
    author: str | None = None
    homepage: str | None = None
    supported_extensions: tuple[str, ...] = Field(default_factory=tuple)
    supported_content_types: tuple[str, ...] = Field(default_factory=tuple)
    priority: int = Field(default=100)
    enabled_by_default: bool = True
    supports_multiline: bool = False
    supports_batch: bool = True
    thread_safe: bool = True
    experimental: bool = False
    tags: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("name", "display_name", "version")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("version must not be empty")
        if not _is_valid_semver(cleaned):
            raise ValueError("version must follow a simple semantic version pattern")
        return cleaned

    @field_validator("description", "author", "homepage")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("supported_extensions")
    @classmethod
    def normalize_extensions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for extension in value:
            cleaned = str(extension).strip().lower()
            if not cleaned:
                continue
            if not cleaned.startswith("."):
                cleaned = f".{cleaned}"
            if cleaned not in seen:
                normalized.append(cleaned)
                seen.add(cleaned)
        return tuple(normalized)

    @field_validator("supported_content_types")
    @classmethod
    def normalize_content_types(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for content_type in value:
            cleaned = str(content_type).strip().lower()
            if not cleaned:
                continue
            if cleaned not in seen:
                normalized.append(cleaned)
                seen.add(cleaned)
        return tuple(normalized)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for tag in value:
            cleaned = str(tag).strip().lower()
            if not cleaned:
                continue
            if cleaned not in seen:
                normalized.append(cleaned)
                seen.add(cleaned)
        return tuple(normalized)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: int) -> int:
        if not 0 <= value <= 1000:
            raise ValueError("priority must be between 0 and 1000")
        return value

    @model_validator(mode="after")
    def validate_identifier_fields(self) -> "ParserMetadata":
        if self.name == self.display_name:
            return self
        return self

    @property
    def identifier(self) -> str:
        return f"{self.name}@{self.version}"

    def supports_extension(self, extension: str) -> bool:
        normalized = _normalize_extension(extension)
        return normalized in self.supported_extensions

    def supports_content_type(self, content_type: str) -> bool:
        normalized = content_type.strip().lower()
        if ";" in normalized:
            normalized = normalized.split(";", 1)[0].strip()
        return normalized in self.supported_content_types


def _is_valid_semver(value: str) -> bool:
    parts = value.split("-")
    core = parts[0]
    if core.count(".") != 2:
        return False
    major, minor, patch = core.split(".")
    if not all(part.isdigit() for part in (major, minor, patch)):
        return False
    return True


def _normalize_extension(extension: str) -> str:
    cleaned = str(extension).strip().lower()
    if not cleaned:
        return ""
    if not cleaned.startswith("."):
        cleaned = f".{cleaned}"
    return cleaned
