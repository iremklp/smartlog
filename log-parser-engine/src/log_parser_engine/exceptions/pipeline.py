from __future__ import annotations


class PipelineError(Exception):
    """Base exception for pipeline orchestration issues."""


class PipelineConfigurationError(PipelineError):
    """Raised when pipeline options or dependencies are invalid."""


class PipelineStageError(PipelineError):
    """Raised when a stage cannot be completed safely."""
