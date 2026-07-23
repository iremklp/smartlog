from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WebErrorClassification(BaseModel):
    """Represents a parsed error-log classification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    category: str = "general"
    event_type: str = "webserver.error.general"
    severity: str = "warning"
    summary: str = "web server error"
    matched_rule: str | None = None
    attributes: dict[str, object] = Field(default_factory=dict)

    @field_validator("category", "event_type", "severity", "summary")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned
