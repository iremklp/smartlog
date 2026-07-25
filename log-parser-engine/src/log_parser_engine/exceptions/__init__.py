
"""Custom exceptions for the Log Parser Engine."""

from .batch import (
    BatchOrchestrationError,
    BatchProcessingError,
    InvalidBatchItemError,
)
from .detection import (
    DetectionError,
    DetectorInternalError,
    DuplicateParserError,
    NoParserFoundError,
    UnsupportedLogFormatError,
)
from .ingestion import (
    ArchiveError,
    ArchiveBombError,
    ArchiveEntrySelectionError,
    ArchiveEntryTooLargeError,
    ArchiveNotAllowedError,
    BinaryContentError,
    EncodingDetectionError,
    EmptyContentError,
    EncryptedArchiveError,
    IngestionError,
    InputNotFoundError,
    InputPermissionError,
    InputSourceError,
    InputTooLargeError,
    SourceReaderError,
    SymlinkNotAllowedError,
    NestedArchiveError,
    TextDecodingError,
)
from .json_parser import (
    JsonDecodingError,
    JsonFieldPathError,
    JsonMappingError,
    JsonParseError,
    JsonParserError,
    JsonProfileError,
    JsonStructureError,
)
from .normalization import NormalizationError
from .parser_registry import (
    ParserAlreadyRegisteredError,
    ParserConfigurationError,
    ParserDiscoveryError,
    ParserNotFoundError,
    ParserRegistrationError,
    ParserRegistrationMismatchError,
)
from .pipeline import PipelineConfigurationError, PipelineError, PipelineStageError
from .plugin import (
    PluginDiscoveryError,
    PluginError,
    PluginLoadError,
    PluginFactoryError,
    PluginValidationError,
)
from .storage import (
    BatchWriteError,
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
from .iis import IisFieldMappingError, IisHeaderError, IisParserError, IisTokenizationError
from .redis import (
    RedisClassificationError,
    RedisMappingError,
    RedisParserError,
    RedisTimestampError,
    RedisTokenizationError,
)
from .syslog import (
    SyslogMappingError,
    SyslogParserError,
    SyslogStructureError,
    SyslogTimestampError,
    SyslogTokenizationError,
)
from .windows_event import (
    WindowsEventMappingError,
    WindowsEventParserError,
    WindowsEventStructureError,
    WindowsEventXmlError,
)

__all__ = [
    # Batch
    "BatchOrchestrationError",
    "BatchProcessingError",
    "InvalidBatchItemError",
    # Detection
    "DetectionError",
    "DetectorInternalError",
    "DuplicateParserError",
    "NoParserFoundError",
    "UnsupportedLogFormatError",
    # Ingestion
    "IngestionError",
    "InputSourceError",
    "InputNotFoundError",
    "InputPermissionError",
    "InputTooLargeError",
    "SymlinkNotAllowedError",
    "BinaryContentError",
    "SourceReaderError",
    "ArchiveError",
    "ArchiveNotAllowedError",
    "ArchiveEntrySelectionError",
    "ArchiveEntryTooLargeError",
    "ArchiveBombError",
    "EncryptedArchiveError",
    "NestedArchiveError",
    "EmptyContentError",
    "EncodingDetectionError",
    # JSON
    "JsonParserError",
    "JsonDecodingError",
    "JsonStructureError",
    "JsonFieldPathError",
    "JsonParseError",
    "JsonMappingError",
    "JsonProfileError",
    # Normalization
    "NormalizationError",
    # Parser Registry
    "ParserAlreadyRegisteredError",
    "ParserNotFoundError",
    "ParserRegistrationError",
    "ParserDiscoveryError",
    "ParserConfigurationError",
    "ParserRegistrationMismatchError",
    # Pipeline
    "PipelineError",
    "PipelineConfigurationError",
    "PipelineStageError",
    # Plugin
    "PluginError",
    "PluginDiscoveryError",
    "PluginLoadError",
    "PluginFactoryError",
    "PluginValidationError",
    # Storage
    "BatchWriteError",
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
    # IIS
    "IisParserError",
    "IisHeaderError",
    "IisTokenizationError",
    "IisFieldMappingError",
    # Redis
    "RedisParserError",
    "RedisTokenizationError",
    "RedisTimestampError",
    "RedisClassificationError",
    "RedisMappingError",
    # Syslog
    "SyslogParserError",
    "SyslogTokenizationError",
    "SyslogTimestampError",
    "SyslogStructureError",
    "SyslogMappingError",
    # Windows Event
    "WindowsEventParserError",
    "WindowsEventXmlError",
    "WindowsEventStructureError",
    "WindowsEventMappingError",
]
