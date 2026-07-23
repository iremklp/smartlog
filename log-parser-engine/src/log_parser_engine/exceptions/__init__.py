"""Exceptions for detection, parser selection, and plugin loading."""

from .detection import DetectionError, DuplicateParserError
from .iis import (
    IisFieldMappingError,
    IisHeaderError,
    IisParserError,
    IisTokenizationError,
)
from .json_parser import (
    JsonDecodingError,
    JsonFieldPathError,
    JsonMappingError,
    JsonParserError,
    JsonProfileError,
    JsonStructureError,
)
from .normalization import NormalizationError
from .parser_registry import (
    ParserAlreadyRegisteredError,
    ParserNotFoundError,
    ParserRegistrationMismatchError,
    ParserRegistryError,
)
from .pipeline import PipelineConfigurationError, PipelineError, PipelineStageError
from .plugin import (
    InvalidPluginError,
    PluginDiscoveryError,
    PluginError,
    PluginFactoryError,
    PluginLoadError,
)
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
    "DetectionError",
    "DuplicateParserError",
    "InvalidPluginError",
    "IisFieldMappingError",
    "IisHeaderError",
    "IisParserError",
    "IisTokenizationError",
    "JsonDecodingError",
    "JsonFieldPathError",
    "JsonMappingError",
    "JsonParserError",
    "JsonProfileError",
    "JsonStructureError",
    "NormalizationError",
    "ParserAlreadyRegisteredError",
    "ParserNotFoundError",
    "ParserRegistrationMismatchError",
    "ParserRegistryError",
    "PipelineConfigurationError",
    "PipelineError",
    "PipelineStageError",
    "PluginDiscoveryError",
    "PluginError",
    "PluginFactoryError",
    "PluginLoadError",
    "RedisClassificationError",
    "RedisMappingError",
    "RedisParserError",
    "RedisTimestampError",
    "RedisTokenizationError",
    "SyslogMappingError",
    "SyslogParserError",
    "SyslogStructureError",
    "SyslogTimestampError",
    "SyslogTokenizationError",
    "WindowsEventMappingError",
    "WindowsEventParserError",
    "WindowsEventStructureError",
    "WindowsEventXmlError",
]
