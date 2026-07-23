from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .detection_candidate import DetectionCandidate


class DetectionDecision(BaseModel):
    """The final outcome of evaluating all available parsers for a log input."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    selected: DetectionCandidate | None = None
    candidates: tuple[DetectionCandidate, ...] = Field(default_factory=tuple)
    minimum_confidence: float = Field(default=0.6)
    ambiguous: bool = False
    ambiguity_margin: float = Field(default=0.05)
    reason: str
    duration_ms: float = Field(default=0.0)
    evaluated_parser_count: int = Field(default=0)
    matched_parser_count: int = Field(default=0)

    @field_validator("minimum_confidence", "ambiguity_margin")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence values must be between 0.0 and 1.0")
        return value

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("reason must not be empty")
        return cleaned

    @field_validator("duration_ms")
    @classmethod
    def validate_duration(cls, value: float) -> float:
        if value < 0:
            raise ValueError("duration_ms must not be negative")
        return value

    @field_validator("evaluated_parser_count", "matched_parser_count")
    @classmethod
    def validate_counts(cls, value: int) -> int:
        if value < 0:
            raise ValueError("count values must not be negative")
        return value

    @model_validator(mode="after")
    def validate_rules(self) -> "DetectionDecision":
        if (
            self.selected is not None
            and self.selected.confidence < self.minimum_confidence
        ):
            raise ValueError("selected candidate must meet the minimum confidence")
        if self.selected is not None and self.selected not in self.candidates:
            raise ValueError("selected candidate must be part of the candidate list")
        if self.selected is None and self.ambiguous:
            raise ValueError("ambiguous decisions must have a selected candidate")
        if self.evaluated_parser_count != len(self.candidates):
            raise ValueError(
                "evaluated_parser_count must match the candidate list length"
            )
        matched_count = sum(1 for candidate in self.candidates if candidate.matched)
        if self.matched_parser_count != matched_count:
            raise ValueError(
                "matched_parser_count must match the number of matched candidates"
            )
        if self.matched_parser_count > self.evaluated_parser_count:
            raise ValueError(
                "matched_parser_count cannot exceed evaluated_parser_count"
            )
        return self

    @property
    def has_match(self) -> bool:
        return self.selected is not None

    @property
    def selected_parser_name(self) -> str | None:
        return self.selected.parser_name if self.selected is not None else None

    @property
    def top_confidence(self) -> float | None:
        if not self.candidates:
            return None
        return max(candidate.confidence for candidate in self.candidates)
