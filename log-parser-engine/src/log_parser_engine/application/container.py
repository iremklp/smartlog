from __future__ import annotations

from datetime import datetime, timezone

from log_parser_engine.batch import BatchParseOrchestrator
from log_parser_engine.core import BaseParser, ParserManager, ParserRegistry
from log_parser_engine.ingestion import FileIngestionService
from log_parser_engine.models import EventStoreStatistics
from log_parser_engine.normalization import LogNormalizer
from log_parser_engine.pipeline import LogProcessingPipeline
from log_parser_engine.storage import EventStore, InMemoryEventStore

from .helpers import build_parser_manager, build_parser_registry
from .options import ApplicationOptions


class ApplicationContainer:
    """Owns application-wide infrastructure objects."""

    def __init__(
        self,
        *,
        options: ApplicationOptions | None = None,
        registry: ParserRegistry | None = None,
        store: EventStore | None = None,
        normalizer: LogNormalizer | None = None,
    ) -> None:
        self.options = options or ApplicationOptions()
        self.created_at = datetime.now(timezone.utc)
        self.startup_warnings: tuple[str, ...] = tuple()
        self.store = store or InMemoryEventStore(self.options.event_store_options)
        self.registry = registry or build_parser_registry(self._build_builtin_parsers())
        self.parser_manager = build_parser_manager(
            self.registry,
            minimum_confidence=self.options.parser_minimum_confidence,
            ambiguity_margin=self.options.parser_ambiguity_margin,
        )
        self.normalizer = normalizer or LogNormalizer()
        self.pipeline = LogProcessingPipeline(self.parser_manager, self.normalizer)
        self.batch_orchestrator = BatchParseOrchestrator(
            self.parser_manager,
            default_options=self.options.batch_parse_options,
        )
        self.ingestion_service = FileIngestionService()

    @classmethod
    def build(
        cls,
        *,
        options: ApplicationOptions | None = None,
        registry: ParserRegistry | None = None,
        store: EventStore | None = None,
        normalizer: LogNormalizer | None = None,
    ) -> "ApplicationContainer":
        return cls(
            options=options,
            registry=registry,
            store=store,
            normalizer=normalizer,
        )

    def store_statistics(self) -> EventStoreStatistics:
        return self.store.statistics()

    def _build_builtin_parsers(self) -> tuple[BaseParser, ...]:
        if not self.options.enable_builtin_parsers:
            return tuple()

        parsers: list[BaseParser] = []
        warnings: list[str] = []

        def attempt(label: str, factory: type[BaseParser]) -> None:
            try:
                parser = factory()
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"{label}: {exc.__class__.__name__}")
                return
            parsers.append(parser)

        try:
            from log_parser_engine.parsers.iis import IisW3CParser
            from log_parser_engine.parsers.json import JsonLogParser
            from log_parser_engine.parsers.redis import RedisLogParser
            from log_parser_engine.parsers.syslog import (
                Rfc3164SyslogParser,
                Rfc5424SyslogParser,
            )
            from log_parser_engine.parsers.webserver import (
                ApacheNginxAccessLogParser,
                ApacheNginxErrorLogParser,
            )
            from log_parser_engine.parsers.windows_event import WindowsEventXmlParser
        except Exception as exc:  # noqa: BLE001
            self.startup_warnings = (f"builtin parser import failed: {exc.__class__.__name__}",)
            return tuple()

        attempt("iis", IisW3CParser)
        attempt("json", JsonLogParser)
        attempt("redis", RedisLogParser)
        attempt("syslog_rfc3164", Rfc3164SyslogParser)
        attempt("syslog_rfc5424", Rfc5424SyslogParser)
        attempt("web_access", ApacheNginxAccessLogParser)
        attempt("web_error", ApacheNginxErrorLogParser)
        attempt("windows_event", WindowsEventXmlParser)

        if warnings:
            self.startup_warnings = tuple(warnings)
        return tuple(parsers)