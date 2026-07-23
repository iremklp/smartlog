from __future__ import annotations

import threading
from typing import Iterable

from log_parser_engine.exceptions import (
    ParserAlreadyRegisteredError,
    ParserNotFoundError,
    ParserRegistrationMismatchError,
)
from log_parser_engine.models import LogSourceType, ParserRegistration

from .base_parser import BaseParser


class ParserRegistry:
    """Registers and manages parser runtime state."""

    def __init__(self, parsers: Iterable[BaseParser] | None = None) -> None:
        self._lock = threading.RLock()
        self._parsers: dict[str, BaseParser] = {}
        self._registrations: dict[str, ParserRegistration] = {}
        self._next_registration_order = 0
        if parsers is not None:
            for parser in parsers:
                self.register(parser)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._parsers)

    @property
    def enabled_count(self) -> int:
        with self._lock:
            return sum(
                1
                for registration in self._registrations.values()
                if registration.enabled
            )

    def __len__(self) -> int:
        return self.count

    def __contains__(self, parser_name: object) -> bool:
        if not isinstance(parser_name, str):
            return False
        return self.contains(parser_name)

    def register(
        self,
        parser: BaseParser,
        *,
        enabled: bool | None = None,
        origin: str | None = "manual",
        notes: str | None = None,
        replace: bool = False,
    ) -> ParserRegistration:
        if not isinstance(parser, BaseParser):
            raise TypeError("parser must be an instance of BaseParser")

        normalized_name = self._normalize_name(parser.name)
        with self._lock:
            existing_parser = self._parsers.get(normalized_name)
            if existing_parser is not None and not replace:
                raise ParserAlreadyRegisteredError(
                    f"parser '{parser.name}' is already registered"
                )

            if existing_parser is not None and replace:
                existing_registration = self._registrations[normalized_name]
                registration_order = existing_registration.registration_order
            else:
                registration_order = self._next_registration_order
                self._next_registration_order += 1

            resolved_enabled = (
                enabled if enabled is not None else parser.metadata.enabled_by_default
            )
            registration = self._build_registration(
                parser=parser,
                enabled=resolved_enabled,
                origin=origin,
                notes=notes,
                registration_order=registration_order,
            )
            self._parsers[normalized_name] = parser
            self._registrations[normalized_name] = registration
            return registration

    def unregister(self, parser_name: str) -> BaseParser:
        normalized_name = self._normalize_name(parser_name)
        with self._lock:
            if normalized_name not in self._parsers:
                raise ParserNotFoundError(f"parser '{parser_name}' was not found")
            parser = self._parsers.pop(normalized_name)
            self._registrations.pop(normalized_name)
            return parser

    def get(self, parser_name: str) -> BaseParser:
        normalized_name = self._normalize_name(parser_name)
        with self._lock:
            if normalized_name not in self._parsers:
                raise ParserNotFoundError(f"parser '{parser_name}' was not found")
            return self._parsers[normalized_name]

    def get_registration(self, parser_name: str) -> ParserRegistration:
        normalized_name = self._normalize_name(parser_name)
        with self._lock:
            if normalized_name not in self._registrations:
                raise ParserNotFoundError(f"parser '{parser_name}' was not found")
            return self._registrations[normalized_name]

    def contains(self, parser_name: str) -> bool:
        try:
            normalized_name = self._normalize_name(parser_name)
        except ValueError:
            return False
        with self._lock:
            return normalized_name in self._parsers

    def list_parsers(self, *, enabled_only: bool = False) -> tuple[BaseParser, ...]:
        with self._lock:
            parsers = []
            for name in self._ordered_names():
                registration = self._registrations[name]
                if enabled_only and not registration.enabled:
                    continue
                parsers.append(self._parsers[name])
            return tuple(parsers)

    def list_registrations(
        self,
        *,
        enabled_only: bool = False,
    ) -> tuple[ParserRegistration, ...]:
        with self._lock:
            registrations = []
            for name in self._ordered_names():
                registration = self._registrations[name]
                if enabled_only and not registration.enabled:
                    continue
                registrations.append(registration)
            return tuple(registrations)

    def find_by_source_type(
        self,
        source_type: LogSourceType,
        *,
        enabled_only: bool = True,
    ) -> tuple[BaseParser, ...]:
        with self._lock:
            matches = []
            for name in self._ordered_names():
                registration = self._registrations[name]
                parser = self._parsers[name]
                if enabled_only and not registration.enabled:
                    continue
                if parser.metadata.source_type == source_type:
                    matches.append(parser)
            return tuple(matches)

    def find_by_tag(
        self,
        tag: str,
        *,
        enabled_only: bool = True,
    ) -> tuple[BaseParser, ...]:
        normalized_tag = self._normalize_tag(tag)
        with self._lock:
            matches = []
            for name in self._ordered_names():
                registration = self._registrations[name]
                parser = self._parsers[name]
                if enabled_only and not registration.enabled:
                    continue
                if normalized_tag in parser.metadata.tags:
                    matches.append(parser)
            return tuple(matches)

    def enable(self, parser_name: str) -> ParserRegistration:
        return self.set_enabled(parser_name, True)

    def disable(self, parser_name: str) -> ParserRegistration:
        return self.set_enabled(parser_name, False)

    def set_enabled(self, parser_name: str, enabled: bool) -> ParserRegistration:
        normalized_name = self._normalize_name(parser_name)
        with self._lock:
            if normalized_name not in self._registrations:
                raise ParserNotFoundError(f"parser '{parser_name}' was not found")
            current = self._registrations[normalized_name]
            if current.enabled == enabled:
                return current
            updated = current.model_copy(update={"enabled": enabled})
            self._registrations[normalized_name] = updated
            return updated

    def clear(self) -> None:
        with self._lock:
            self._parsers.clear()
            self._registrations.clear()
            self._next_registration_order = 0

    def _build_registration(
        self,
        *,
        parser: BaseParser,
        enabled: bool,
        origin: str | None,
        notes: str | None,
        registration_order: int,
    ) -> ParserRegistration:
        metadata = parser.metadata
        registration = ParserRegistration(
            parser_name=parser.name,
            parser_version=parser.version,
            source_type=parser.source_type,
            enabled=enabled,
            registration_order=registration_order,
            metadata=metadata,
            origin=origin,
            notes=notes,
        )
        if registration.metadata.source_type != parser.source_type:
            raise ParserRegistrationMismatchError(
                "registration metadata is inconsistent with parser metadata"
            )
        return registration

    def _ordered_names(self) -> list[str]:
        return sorted(
            self._registrations,
            key=lambda name: self._registrations[name].registration_order,
        )

    def _normalize_name(self, parser_name: str) -> str:
        cleaned = parser_name.strip().casefold()
        if not cleaned:
            raise ValueError("parser_name must not be empty")
        return cleaned

    def _normalize_tag(self, tag: str) -> str:
        cleaned = tag.strip().lower()
        if not cleaned:
            raise ValueError("tag must not be empty")
        return cleaned
