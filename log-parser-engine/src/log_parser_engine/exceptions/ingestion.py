from __future__ import annotations


class IngestionError(Exception):
    """Base class for ingestion failures."""


class InputSourceError(IngestionError):
    """Raised when the input source is invalid or unsupported."""


class SourceReaderError(InputSourceError):
    """Backward-compatible alias for source reader failures."""


class InputNotFoundError(InputSourceError):
    """Raised when a path source cannot be found."""


class InputPermissionError(InputSourceError):
    """Raised when a path source cannot be accessed."""


class InputTooLargeError(InputSourceError):
    """Raised when the input exceeds configured size limits."""


class SymlinkNotAllowedError(InputSourceError):
    """Raised when symlink following is disabled for a path source."""


class BinaryContentError(IngestionError):
    """Raised when binary-like content is rejected."""


class EncodingDetectionError(IngestionError):
    """Raised when encoding detection cannot resolve a safe codec."""


class TextDecodingError(IngestionError):
    """Raised when bytes cannot be decoded into text."""


class ArchiveError(IngestionError):
    """Base class for archive handling failures."""


class ArchiveNotAllowedError(ArchiveError):
    """Raised when an archive type is disabled by options."""


class ArchiveEntrySelectionError(ArchiveError):
    """Raised when archive entry selection fails."""


class ArchiveEntryTooLargeError(ArchiveError):
    """Raised when an archive entry exceeds configured limits."""


class ArchiveBombError(ArchiveError):
    """Raised when archive expansion appears unsafe."""


class EncryptedArchiveError(ArchiveError):
    """Raised when an encrypted archive is rejected."""


class NestedArchiveError(ArchiveError):
    """Raised when a nested archive is rejected."""


class EmptyContentError(IngestionError):
    """Raised when input resolves to empty content and empty input is disallowed."""