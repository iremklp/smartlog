from __future__ import annotations


class WindowsEventParserError(Exception):
    """Base class for Windows Event XML parser errors."""


class WindowsEventXmlError(WindowsEventParserError):
    """Raised when the Windows Event XML payload cannot be parsed safely."""


class WindowsEventStructureError(WindowsEventParserError):
    """Raised when the Windows Event XML structure is unsupported."""


class WindowsEventMappingError(WindowsEventParserError):
    """Raised when Windows Event data cannot be mapped to canonical fields."""