from __future__ import annotations


class BatchParseError(Exception):
    """Base exception for fatal batch orchestration failures."""


class BatchConfigurationError(BatchParseError):
    """Raised when batch options or orchestration setup is invalid."""


class BatchDetectionError(BatchParseError):
    """Raised when parser detection fails at orchestration level."""


class BatchRecordTooLargeError(BatchParseError):
    """Raised when a record exceeds the configured character limit."""

    def __init__(
        self,
        *,
        record_index: int,
        character_count: int,
        max_characters: int,
    ) -> None:
        super().__init__("record exceeds max_record_characters")
        self.record_index = record_index
        self.character_count = character_count
        self.max_characters = max_characters


class BatchErrorLimitExceeded(BatchParseError):
    """Raised when the total error limit is reached."""


class BatchErrorRateExceeded(BatchParseError):
    """Raised when error rate exceeds threshold."""


class BatchConsecutiveErrorLimitExceeded(BatchParseError):
    """Raised when consecutive error limit is reached."""


class BatchMixedFormatError(BatchParseError):
    """Raised when mixed parser formats are not allowed."""


class BatchUnsupportedRecordModeError(BatchParseError):
    """Raised when a record mode is incompatible with parser strategy."""


class BatchProgressCallbackError(BatchParseError):
    """Raised when progress callback fails."""


class BatchStateError(BatchParseError):
    """Raised when parser state transitions are invalid."""


class BatchSourceError(BatchParseError):
    """Raised when source iteration or streaming fails."""
