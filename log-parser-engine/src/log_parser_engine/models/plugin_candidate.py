from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PluginCandidate(BaseModel):
    """Immutable descriptor for a discovered plugin candidate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    source: str
    module_name: str
    object_name: str | None = None
    entry_point_group: str | None = None
    entry_point_name: str | None = None
    origin: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "source", "module_name", "origin")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned

    @field_validator("object_name", "entry_point_group", "entry_point_name")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @property
    def qualified_name(self) -> str:
        if self.object_name is not None:
            return f"{self.module_name}:{self.object_name}"
        return self.module_name
