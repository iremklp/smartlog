from enum import Enum
from typing import Self


class _CaseInsensitiveStringEnum(str, Enum):
    """String enum with lowercase wire values and legacy input support."""

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def _missing_(cls, value: object) -> Self | None:
        if not isinstance(value, str):
            return None

        normalized = value.strip().casefold()
        for member in cls:
            if (
                member.value.casefold() == normalized
                or member.name.casefold() == normalized
            ):
                return member
        return None


class LogSeverity(_CaseInsensitiveStringEnum):
    UNKNOWN = "unknown"
    unknown = "unknown"
    TRACE = "trace"
    trace = "trace"
    DEBUG = "debug"
    debug = "debug"
    INFO = "info"
    info = "info"
    WARNING = "warning"
    warning = "warning"
    ERROR = "error"
    error = "error"
    CRITICAL = "critical"
    critical = "critical"
    NOTICE = "notice"
    notice = "notice"
    FATAL = "fatal"
    fatal = "fatal"


class LogSourceType(_CaseInsensitiveStringEnum):
    UNKNOWN = "unknown"
    unknown = "unknown"
    FILE = "file"
    file = "file"
    SYSLOG = "syslog"
    syslog = "syslog"
    HTTP = "http"
    http = "http"
    DATABASE = "database"
    database = "database"
    WINDOWS_EVENT = "windows_event"
    windows_event = "windows_event"
    APPLICATION = "application"
    application = "application"
    IIS = "iis"
    iis = "iis"
    REDIS = "redis"
    redis = "redis"
    JSON = "json"
    json = "json"
    XML = "xml"
    xml = "xml"
    CSV = "csv"
    csv = "csv"
    NGINX = "nginx"
    nginx = "nginx"
    APACHE = "apache"
    apache = "apache"
    LINUX_SYSLOG = "linux_syslog"
    linux_syslog = "linux_syslog"
    KUBERNETES = "kubernetes"
    kubernetes = "kubernetes"
    OPENSHIFT = "openshift"
    openshift = "openshift"
    JENKINS = "jenkins"
    jenkins = "jenkins"


class ParseStatus(_CaseInsensitiveStringEnum):
    SUCCESS = "success"
    success = "success"
    FAILURE = "failed"
    FAILED = "failed"
    failed = "failed"
    failure = "failed"
    PARTIAL = "partial"
    partial = "partial"


class ErrorType(_CaseInsensitiveStringEnum):
    UNKNOWN = "unknown"
    unknown = "unknown"
    PARSING = "parsing"
    parsing = "parsing"
    VALIDATION = "validation"
    validation = "validation"
    INGESTION = "ingestion"
    ingestion = "ingestion"
    UNKNOWN_FORMAT = "unknown_format"
    unknown_format = "unknown_format"
    EMPTY_INPUT = "empty_input"
    empty_input = "empty_input"
    INTERNAL_ERROR = "internal_error"
    internal_error = "internal_error"
    DETECTION_FAILED = "detection_failed"
    detection_failed = "detection_failed"
    PARSE_FAILED = "parse_failed"
    parse_failed = "parse_failed"
    VALIDATION_FAILED = "validation_failed"
    validation_failed = "validation_failed"
    INVALID_TIMESTAMP = "invalid_timestamp"
    invalid_timestamp = "invalid_timestamp"
    INVALID_ENCODING = "invalid_encoding"
    invalid_encoding = "invalid_encoding"
