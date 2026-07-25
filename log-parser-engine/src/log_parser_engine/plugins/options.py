from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PluginStartupOptions(BaseModel):
    """Immutable, opt-in configuration for trusted startup plugins."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    package_names: tuple[str, ...] = Field(default_factory=tuple)
    enable_entry_points: bool = False
    entry_point_group: str = "log_parser_engine.parsers"
    entry_point_names: tuple[str, ...] = Field(default_factory=tuple)
    duplicate_policy: Literal["reject", "replace"] = "reject"
    failure_policy: Literal["fail", "warn"] = "fail"
    require_package_manifest: bool = True
    allow_injected_loaders: bool = False
    allow_builtin_replacement: bool = False
    allow_experimental_plugins: bool = False
    require_thread_safe_plugins: bool = True
    max_candidates: int = Field(default=100, ge=1, le=1_000)
    max_startup_warnings: int = Field(default=20, ge=1, le=100)
    max_warning_length: int = Field(default=256, ge=64, le=1_024)

    @field_validator("package_names")
    @classmethod
    def normalize_package_names(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return cls._normalize_dotted_names(value, field_name="package_names")

    @field_validator("entry_point_group")
    @classmethod
    def validate_entry_point_group(cls, value: str) -> str:
        cleaned = value.strip()
        cls._validate_dotted_name(cleaned, field_name="entry_point_group")
        return cleaned

    @field_validator("entry_point_names")
    @classmethod
    def normalize_entry_point_names(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        seen: set[str] = set()
        normalized: list[str] = []
        for raw_name in value:
            cleaned = str(raw_name).strip()
            if not cleaned:
                continue
            if len(cleaned) > 128:
                raise ValueError("entry_point_names entries must not exceed 128 chars")
            if any(ord(character) < 32 for character in cleaned):
                raise ValueError("entry_point_names entries contain control characters")
            if cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)
        return tuple(normalized)

    @model_validator(mode="after")
    def validate_entry_point_configuration(self) -> "PluginStartupOptions":
        if self.enable_entry_points and not self.entry_point_names:
            raise ValueError(
                "entry_point_names must not be empty when entry points are enabled"
            )
        return self

    @property
    def enabled(self) -> bool:
        """Return whether at least one configured startup source is active."""

        return bool(
            self.package_names
            or self.enable_entry_points
            or self.allow_injected_loaders
        )

    @classmethod
    def _normalize_dotted_names(
        cls,
        values: tuple[str, ...],
        *,
        field_name: str,
    ) -> tuple[str, ...]:
        seen: set[str] = set()
        normalized: list[str] = []
        for raw_value in values:
            cleaned = str(raw_value).strip()
            if not cleaned:
                continue
            cls._validate_dotted_name(cleaned, field_name=field_name)
            if cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)
        return tuple(normalized)

    @staticmethod
    def _validate_dotted_name(value: str, *, field_name: str) -> None:
        if not value or len(value) > 255:
            raise ValueError(f"{field_name} contains an invalid dotted name")
        parts = value.split(".")
        if any(
            not part.isidentifier() or part.startswith("_")
            for part in parts
        ):
            raise ValueError(f"{field_name} contains an invalid dotted name")
