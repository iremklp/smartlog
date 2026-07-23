from __future__ import annotations


class SyslogParserError(Exception):
    """Base class for syslog parser errors."""


class SyslogTokenizationError(SyslogParserError):
    """Raised when syslog tokenization fails."""


class SyslogTimestampError(SyslogParserError):
    """Raised when a syslog timestamp cannot be parsed."""


class SyslogStructureError(SyslogParserError):
    """Raised when a syslog message structure is unsupported."""


class SyslogMappingError(SyslogParserError):
    """Raised when syslog mapping to canonical fields fails."""