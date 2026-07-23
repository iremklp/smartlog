from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from log_parser_engine.pipeline.stages import PipelineStage


class PipelineStageResult(BaseModel):
    """Immutable result of one pipeline stage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    stage: PipelineStage
    success: bool
    skipped: bool = False
    duration_ms: float
    message: str | None = None
    error_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("duration_ms")
    @classmethod
    def validate_duration(cls, value: float) -> float:
        if value < 0:
            raise ValueError("duration_ms must not be negative")
        return value

    @field_validator("message", "error_type")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_rules(self) -> "PipelineStageResult":
        if self.skipped:
            if not self.success:
                raise ValueError("skipped stages must be successful")
            if self.error_type is not None:
                raise ValueError("skipped stages must not have an error_type")
            return self
        if self.success:
            if self.error_type is not None:
                raise ValueError("successful stages must not have an error_type")
            return self
        if self.message is None and self.error_type is None:
            raise ValueError("failed stages must include a message or error_type")
        return self

    @classmethod
    def succeeded(
        cls,
        *,
        stage: PipelineStage,
        duration_ms: float,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "PipelineStageResult":
        return cls(
            stage=stage,
            success=True,
            duration_ms=duration_ms,
            message=message,
            metadata=metadata or {},
        )

    @classmethod
    def failed(
        cls,
        *,
        stage: PipelineStage,
        duration_ms: float,
        error_type: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> "PipelineStageResult":
        return cls(
            stage=stage,
            success=False,
            duration_ms=duration_ms,
            error_type=error_type,
            message=message,
            metadata=metadata or {},
        )

    @classmethod
    def skipped_result(
        cls,
        *,
        stage: PipelineStage,
        message: str,
    ) -> "PipelineStageResult":
        return cls(
            stage=stage,
            success=True,
            skipped=True,
            duration_ms=0.0,
            message=message,
        )

    @property
    def terminal_failure(self) -> bool:
        return not self.success and not self.skipped
