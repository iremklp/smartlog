from __future__ import annotations

from enum import Enum


class PipelineStage(str, Enum):
    """Ordered stages for a single log processing pipeline run."""

    INPUT_VALIDATION = "input_validation"
    PARSER_SELECTION = "parser_selection"
    PARSING = "parsing"
    NORMALIZATION = "normalization"
    COMPLETED = "completed"

    def __str__(self) -> str:
        return str(self.value)


def ordered_stages() -> tuple[PipelineStage, ...]:
    return (
        PipelineStage.INPUT_VALIDATION,
        PipelineStage.PARSER_SELECTION,
        PipelineStage.PARSING,
        PipelineStage.NORMALIZATION,
        PipelineStage.COMPLETED,
    )
