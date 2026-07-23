"""Exceptions for detection, parser selection, and plugin loading."""

from .detection import DetectionError, DuplicateParserError
from .iis import (
    IisFieldMappingError,
    IisHeaderError,
    IisParserError,
    IisTokenizationError,
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

__all__ = [
    "DetectionError",
    "DuplicateParserError",
    "InvalidPluginError",
    "IisFieldMappingError",
    "IisHeaderError",
    "IisParserError",
    "IisTokenizationError",
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
]
