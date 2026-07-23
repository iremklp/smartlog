from enum import Enum


class StrEnum(str, Enum):
    """String-backed enum with lowercase JSON serialization values."""

    def __str__(self) -> str:
        return str(self.value)


class LogSeverity(StrEnum):
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"
    UNKNOWN = "unknown"

    trace = TRACE
    debug = DEBUG
    info = INFO
    notice = NOTICE
    warning = WARNING
    error = ERROR
    critical = CRITICAL
    fatal = FATAL
    unknown = UNKNOWN


class LogSourceType(StrEnum):
    IIS = "iis"
    REDIS = "redis"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    NGINX = "nginx"
    APACHE = "apache"
    WINDOWS_EVENT = "windows_event"
    SYSLOG = "syslog"
    LINUX_SYSLOG = "linux_syslog"
    KUBERNETES = "kubernetes"
    OPENSHIFT = "openshift"
    JENKINS = "jenkins"
    APPLICATION = "application"
    UNKNOWN = "unknown"

    iis = IIS
    redis = REDIS
    json = JSON
    xml = XML
    csv = CSV
    nginx = NGINX
    apache = APACHE
    windows_event = WINDOWS_EVENT
    syslog = SYSLOG
    linux_syslog = LINUX_SYSLOG
    kubernetes = KUBERNETES
    openshift = OPENSHIFT
    jenkins = JENKINS
    application = APPLICATION
    unknown = UNKNOWN


class ParseStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"

    success = SUCCESS
    partial = PARTIAL
    failed = FAILED


class ErrorType(StrEnum):
    UNKNOWN_FORMAT = "unknown_format"
    DETECTION_FAILED = "detection_failed"
    PARSE_FAILED = "parse_failed"
    VALIDATION_FAILED = "validation_failed"
    INVALID_TIMESTAMP = "invalid_timestamp"
    INVALID_ENCODING = "invalid_encoding"
    EMPTY_INPUT = "empty_input"
    INTERNAL_ERROR = "internal_error"

    unknown_format = UNKNOWN_FORMAT
    detection_failed = DETECTION_FAILED
    parse_failed = PARSE_FAILED
    validation_failed = VALIDATION_FAILED
    invalid_timestamp = INVALID_TIMESTAMP
    invalid_encoding = INVALID_ENCODING
    empty_input = EMPTY_INPUT
    internal_error = INTERNAL_ERROR
