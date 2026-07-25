"""Categorical distribution analysis models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .ranked_item import RankedItem


class DistributionResult(BaseModel):
    """A bounded top-N distribution over all filtered events.

    Item percentages use ``total_count`` as their denominator so missing values
    remain visible in the result.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str
    total_count: int = Field(ge=0)
    matched_value_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    unique_value_count: int = Field(ge=0)
    items: tuple[RankedItem, ...] = ()
    other_count: int = Field(default=0, ge=0)
    truncated: bool = False

    @field_validator("field")
    @classmethod
    def _field(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("distribution field must not be empty")
        return cleaned

    @model_validator(mode="after")
    def _count_consistency(self) -> "DistributionResult":
        # Multi-valued fields such as tags can contribute more than one matched
        # value per event. Missing remains event-based and cannot exceed total.
        if self.missing_count > self.total_count:
            raise ValueError("missing_count cannot exceed total_count")
        if sum(item.count for item in self.items) + self.other_count != (
            self.matched_value_count
        ):
            raise ValueError(
                "ranked item counts and other_count must equal matched_value_count"
            )
        if self.unique_value_count < len(self.items):
            raise ValueError("unique_value_count cannot be smaller than returned items")
        expected_ranks = tuple(range(1, len(self.items) + 1))
        if tuple(item.rank for item in self.items) != expected_ranks:
            raise ValueError("ranked items must use contiguous 1-based ranks")
        return self
