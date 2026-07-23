from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PipelineOptions(BaseModel):
    """Immutable options that control a single pipeline execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    parser_name: str | None = None
    allow_disabled_parser: bool = False
    normalize: bool = True
    strict_normalization: bool | None = None
    preserve_unknown_fields: bool | None = None
    fail_on_ambiguity: bool = False
    minimum_confidence_override: float | None = None
    ambiguity_margin_override: float | None = None
    include_stage_results: bool = True
    include_detection_candidates: bool = True
    max_raw_error_length: int = Field(default=500)

    @field_validator("parser_name")
    @classmethod
    def normalize_parser_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("minimum_confidence_override", "ambiguity_margin_override")
    @classmethod
    def validate_confidence_overrides(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not 0.0 <= value <= 1.0:
            raise ValueError("override value must be between 0.0 and 1.0")
        return value

    @field_validator("max_raw_error_length")
    @classmethod
    def validate_max_raw_error_length(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("max_raw_error_length must be greater than 0")
        return value

    @property
    def manual_parser_requested(self) -> bool:
        return self.parser_name is not None
