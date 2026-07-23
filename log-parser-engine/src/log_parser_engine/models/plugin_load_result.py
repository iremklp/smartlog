from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .plugin_candidate import PluginCandidate


class PluginLoadResult(BaseModel):
    """Immutable outcome for a single plugin load attempt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate: PluginCandidate
    success: bool
    parser_name: str | None = None
    parser_version: str | None = None
    registered: bool = False
    replaced_existing: bool = False
    error_type: str | None = None
    error_message: str | None = None
    duration_ms: float = Field(default=0.0, ge=0.0)

    @field_validator("error_type", "error_message")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_state(self) -> "PluginLoadResult":
        if self.success:
            if self.parser_name is None or self.parser_version is None:
                raise ValueError(
                    "successful loads require parser_name and parser_version"
                )
            if self.error_type is not None or self.error_message is not None:
                raise ValueError("successful loads must not carry error details")
            if self.replaced_existing and not self.registered:
                raise ValueError("replaced_existing requires registered=True")
            return self

        if self.registered:
            raise ValueError("failed loads cannot be registered")
        if self.replaced_existing:
            raise ValueError("failed loads cannot report replaced_existing")
        if self.error_type is None and self.error_message is None:
            raise ValueError("failed loads require error_type or error_message")
        return self

    @property
    def identifier(self) -> str | None:
        if self.parser_name is None or self.parser_version is None:
            return None
        return f"{self.parser_name}@{self.parser_version}"

    @classmethod
    def loaded(
        cls,
        *,
        candidate: PluginCandidate,
        parser_name: str,
        parser_version: str,
        registered: bool,
        replaced_existing: bool = False,
        duration_ms: float = 0.0,
    ) -> "PluginLoadResult":
        return cls(
            candidate=candidate,
            success=True,
            parser_name=parser_name,
            parser_version=parser_version,
            registered=registered,
            replaced_existing=replaced_existing,
            duration_ms=duration_ms,
        )

    @classmethod
    def failed(
        cls,
        *,
        candidate: PluginCandidate,
        error_type: str,
        error_message: str,
        duration_ms: float = 0.0,
    ) -> "PluginLoadResult":
        return cls(
            candidate=candidate,
            success=False,
            error_type=error_type,
            error_message=error_message,
            duration_ms=duration_ms,
        )
