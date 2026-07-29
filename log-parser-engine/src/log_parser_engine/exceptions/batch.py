
from __future__ import annotations


class BatchOrchestrationError(Exception):
    """Base exception for batch orchestration failures."""


class BatchProcessingError(BatchOrchestrationError):
    """Raised when a batch cannot be processed safely."""


class InvalidBatchItemError(BatchProcessingError):
    """Raised when a batch item is malformed or unsupported."""


class BatchConfigurationError(BatchOrchestrationError):
    """Raised when batch configuration is invalid."""


class BatchDetectionError(BatchOrchestrationError):
    """Raised when parser detection fails during batch processing."""


class BatchMixedFormatError(BatchOrchestrationError):
    """Raised when multiple incompatible record formats are detected."""


class BatchProgressCallbackError(BatchOrchestrationError):
    """Raised when a progress callback fails."""


class BatchRecordTooLargeError(BatchOrchestrationError):
    """Raised when a batch record exceeds configured limits."""

    def __init__(
        self,
        message: str | None = None,
        *,
        record_index: int | None = None,
        character_count: int | None = None,
        max_characters: int | None = None,
    ) -> None:
        self.record_index = record_index
        self.character_count = character_count
        self.max_characters = max_characters
        if message is None:
            if None in {record_index, character_count, max_characters}:
                raise TypeError(
                    "record_index, character_count, and max_characters are required "
                    "when message is omitted"
                )
            message = (
                f"Batch record {record_index} contains {character_count} characters; "
                f"the configured limit is {max_characters}."
            )
        super().__init__(message)


class BatchSourceError(BatchOrchestrationError):
    """Raised when the batch source cannot be consumed safely."""


class BatchUnsupportedRecordModeError(BatchOrchestrationError):
    """Raised when a record mode is unsupported by the orchestrator."""


class BatchErrorLimitExceeded(BatchOrchestrationError):
    """Raised when the configured error limit is exceeded."""


class BatchConsecutiveErrorLimitExceeded(BatchOrchestrationError):
    """Raised when the consecutive error limit is exceeded."""


class BatchErrorRateExceeded(BatchOrchestrationError):
    """Raised when the batch error-rate threshold is exceeded."""
