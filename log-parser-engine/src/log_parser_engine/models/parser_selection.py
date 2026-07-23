from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from .detection_decision import DetectionDecision
from .enums import LogSourceType


class ParserSelection(BaseModel):
    """Immutable result of selecting a parser through the manager."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    parser_name: str | None = None
    parser_version: str | None = None
    source_type: LogSourceType | None = None
    confidence: float | None = None
    ambiguous: bool = False
    reason: str
    decision: DetectionDecision

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("reason must not be empty")
        return cleaned

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value

    @model_validator(mode="after")
    def validate_selection_rules(self) -> "ParserSelection":
        if self.parser_name is None:
            if self.parser_version is not None:
                raise ValueError("parser_version requires a parser_name")
            if self.source_type is not None:
                raise ValueError("source_type requires a parser_name")
            if self.confidence is not None:
                raise ValueError("confidence requires a parser_name")
            if self.ambiguous:
                raise ValueError("ambiguous selection requires a parser_name")
            return self

        if self.parser_version is None:
            raise ValueError("parser_version is required when a parser is selected")
        if self.source_type is None:
            raise ValueError("source_type is required when a parser is selected")
        if self.confidence is None:
            raise ValueError("confidence is required when a parser is selected")
        if self.decision.selected is None:
            raise ValueError("selected decision must contain a selected candidate")
        if self.decision.selected.parser_name != self.parser_name:
            raise ValueError("parser_name must match the decision selection")
        if self.decision.selected.parser_version != self.parser_version:
            raise ValueError("parser_version must match the decision selection")
        if self.decision.selected.source_type != self.source_type:
            raise ValueError("source_type must match the decision selection")
        if self.decision.selected.confidence != self.confidence:
            raise ValueError("confidence must match the decision selection")
        if self.ambiguous != self.decision.ambiguous:
            raise ValueError("ambiguous must match the decision ambiguity")
        return self

    @property
    def selected(self) -> bool:
        return self.parser_name is not None

    @property
    def identifier(self) -> str | None:
        if self.parser_name is None or self.parser_version is None:
            return None
        return f"{self.parser_name}@{self.parser_version}"

    @classmethod
    def from_decision(cls, decision: DetectionDecision) -> "ParserSelection":
        if decision.selected is None:
            return cls(
                parser_name=None,
                parser_version=None,
                source_type=None,
                confidence=None,
                ambiguous=False,
                reason=decision.reason,
                decision=decision,
            )
        selected = decision.selected
        return cls(
            parser_name=selected.parser_name,
            parser_version=selected.parser_version,
            source_type=selected.source_type,
            confidence=selected.confidence,
            ambiguous=decision.ambiguous,
            reason=decision.reason,
            decision=decision,
        )
