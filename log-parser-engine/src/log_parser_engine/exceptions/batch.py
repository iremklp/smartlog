
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
