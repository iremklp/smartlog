
from enum import Enum


class LogSeverity(str, Enum):
    UNKNOWN = "UNKNOWN"
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogSourceType(str, Enum):
    UNKNOWN = "UNKNOWN"
    FILE = "FILE"
    SYSLOG = "SYSLOG"
    HTTP = "HTTP"
    DATABASE = "DATABASE"
    WINDOWS_EVENT = "WINDOWS_EVENT"


class ParseStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL = "PARTIAL"

class ErrorType(str, Enum):
    UNKNOWN = "UNKNOWN"
    PARSING = "PARSING"
    VALIDATION = "VALIDATION"
    INGESTION = "INGESTION"
    UNKNOWN_FORMAT = "UNKNOWN_FORMAT"
