
"""Custom exceptions for the Log Parser Engine."""

from .batch import (
    BatchOrchestrationError,
    BatchProcessingError,
    InvalidBatchItemError,
)
from .detection import (
    DetectionError,
    DetectorInternalError,
    NoParserFoundError,
    UnsupportedLogFormatError,
)
from .ingestion import (
    ArchiveError,
    EncodingDetectionError,
    IngestionError,
    SourceReaderError,
)
from .json_parser import JsonParseError, JsonProfileError
from .normalization import NormalizationError
from .parser_registry import (
    ParserConfigurationError,
    ParserDiscoveryError,
    ParserRegistrationError,
)
from .pipeline import PipelineError, PipelineStageError
from .plugin import (
    PluginDiscoveryError,
    PluginError,
    PluginLoadError,
    PluginValidationError,
)
from .storage import (
    DuplicateEventError,
    EventAggregationError,
    EventFilterError,
    EventIdCollisionError,
    EventPaginationError,
    EventQueryError,
    EventSnapshotError,
    EventSortError,
    EventStoreCapacityError,
    EventStoreConfigurationError,
    EventStoreError,
    EventTooLargeForStoreError,
    InvalidEventError,
    InvalidEventIdError,
)

__all__ = [
    # Batch
    "BatchOrchestrationError",
    "BatchProcessingError",
    "InvalidBatchItemError",
    # Detection
    "DetectionError",
    "DetectorInternalError",
    "NoParserFoundError",
    "UnsupportedLogFormatError",
    # Ingestion
    "IngestionError",
    "SourceReaderError",
    "ArchiveError",
    "EncodingDetectionError",
    # JSON
    "JsonParseError",
    "JsonProfileError",
    # Normalization
    "NormalizationError",
    # Parser Registry
    "ParserRegistrationError",
    "ParserDiscoveryError",
    "ParserConfigurationError",
    # Pipeline
    "PipelineError",
    "PipelineStageError",
    # Plugin
    "PluginError",
    "PluginDiscoveryError",
    "PluginLoadError",
    "PluginValidationError",
    # Storage
    "EventStoreError",
    "EventStoreConfigurationError",
    "InvalidEventError",
    "InvalidEventIdError",
    "DuplicateEventError",
    "EventIdCollisionError",
    "EventStoreCapacityError",
    "EventTooLargeForStoreError",
    "EventQueryError",
    "EventFilterError",
    "EventSortError",
    "EventPaginationError",
    "EventAggregationError",
    "EventSnapshotError",
]
