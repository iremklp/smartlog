"""Top-level orchestration for deterministic statistical event analysis."""

from __future__ import annotations

from collections.abc import Sequence
from time import perf_counter

from log_parser_engine.exceptions.analysis import (
    AnalysisEventLimitError,
    AnalysisRequestError,
)
from log_parser_engine.models.analysis_request import AnalysisRequest, ComparisonRequest
from log_parser_engine.models.analysis_result import AnalysisEventSample, AnalysisResult
from log_parser_engine.models.comparison_result import ComparisonResult
from log_parser_engine.models.event_filter import EventFilter
from log_parser_engine.models.stored_event import StoredEvent
from log_parser_engine.storage.base import EventStore
from log_parser_engine.storage.query_engine import matches_event_filter

from .distributions import build_distributions
from .extractors import (
    get_event_type,
    get_host,
    get_parser_name,
    get_service,
)
from .helpers import bounded_preview
from .http_analysis import analyze_http
from .insights import generate_insights
from .latency import analyze_latency
from .options import AnalysisOptions
from .sampling import deterministic_sample
from .summary import summarize_events
from .timelines import build_timeline


class StatisticalAnalysisEngine:
    """Stateless coordinator over immutable ``StoredEvent`` snapshots."""

    def __init__(self, options: AnalysisOptions | None = None) -> None:
        self._options = options or AnalysisOptions()
        if not isinstance(self._options, AnalysisOptions):
            raise TypeError("options must be an AnalysisOptions instance")

    @property
    def options(self) -> AnalysisOptions:
        return self._options

    def analyze(
        self,
        events: Sequence[StoredEvent],
        request: AnalysisRequest,
    ) -> AnalysisResult:
        """Analyze a bounded immutable snapshot without mutating its events."""
        self._validate_inputs(events, request)
        started = perf_counter()
        input_event_count = len(events)
        matched_events = self._filter_events(events, request)
        top_n = request.top_n or self._options.default_top_n

        summary = (
            summarize_events(
                matched_events,
                input_event_count=input_event_count,
                duration_field=request.duration_field,
                status_field=request.status_field,
                options=self._options,
            )
            if request.include_summary or request.include_insights
            else None
        )
        distributions = (
            build_distributions(
                matched_events,
                fields=request.group_fields,
                top_n=top_n,
                options=self._options,
            )
            if request.include_distributions
            else tuple()
        )
        timeline = (
            build_timeline(matched_events, request, options=self._options)
            if request.include_timeline
            else None
        )
        latency = (
            analyze_latency(matched_events, request, options=self._options)
            if request.include_latency
            else None
        )
        http = (
            analyze_http(matched_events, request, options=self._options)
            if request.include_http
            else None
        )
        insights = (
            generate_insights(
                summary=summary,
                distributions=distributions,
                latency=latency,
                http=http,
                timeline=timeline,
                options=self._options,
            )
            if request.include_insights and summary is not None
            else tuple()
        )
        samples = (
            self._build_samples(matched_events, request.sample_size)
            if request.include_samples
            else tuple()
        )
        warnings = self._collect_warnings(timeline, latency, http)
        duration_ms = (perf_counter() - started) * 1000.0
        return AnalysisResult(
            request=request,
            summary=summary if request.include_summary else None,
            timeline=timeline,
            distributions=distributions,
            latency=latency,
            http=http,
            insights=insights,
            samples=samples,
            input_event_count=input_event_count,
            matched_event_count=len(matched_events),
            analysis_duration_ms=duration_ms,
            warnings=warnings,
            metadata=request.metadata,
        )

    def compare(
        self,
        baseline_events: Sequence[StoredEvent],
        comparison_events: Sequence[StoredEvent],
        request: ComparisonRequest,
    ) -> ComparisonResult:
        """Compare two snapshots using the same deterministic analysis semantics."""
        from .comparison import compare_event_snapshots

        return compare_event_snapshots(
            baseline_events,
            comparison_events,
            request,
            options=self._options,
        )

    def _validate_inputs(
        self,
        events: Sequence[StoredEvent],
        request: AnalysisRequest,
    ) -> None:
        if not isinstance(request, AnalysisRequest):
            raise TypeError("request must be an AnalysisRequest")
        if isinstance(events, (str, bytes)) or not isinstance(events, Sequence):
            raise TypeError("events must be a sequence of StoredEvent instances")
        if len(events) > self._options.max_events:
            raise AnalysisEventLimitError(len(events), self._options.max_events)
        if (
            request.top_n is not None
            and request.top_n > self._options.max_top_n
        ):
            raise AnalysisRequestError(
                "analysis top_n exceeds the configured limit"
            )
        if len(request.group_fields) > self._options.max_group_fields_per_request:
            raise AnalysisRequestError(
                "analysis group field count exceeds the configured limit"
            )
        if len(request.percentiles) > self._options.max_percentiles_per_request:
            raise AnalysisRequestError(
                "analysis percentile count exceeds the configured limit"
            )
        if (
            request.time_bucket_seconds is not None
            and request.time_bucket_seconds
            > self._options.max_time_bucket_seconds
        ):
            raise AnalysisRequestError(
                "analysis timeline bucket size exceeds the configured limit"
            )
        if request.sample_size > self._options.max_samples_per_request:
            raise AnalysisRequestError(
                "analysis sample size exceeds the configured limit"
            )
        if any(not isinstance(event, StoredEvent) for event in events):
            raise TypeError("events must contain only StoredEvent instances")

    def _filter_events(
        self,
        events: Sequence[StoredEvent],
        request: AnalysisRequest,
    ) -> tuple[StoredEvent, ...]:
        event_filter = request.filter or EventFilter()
        matched: list[StoredEvent] = []
        for event in events:
            if not matches_event_filter(event, event_filter):
                continue
            if request.start_time is not None and event.timestamp < request.start_time:
                continue
            if request.end_time is not None and event.timestamp >= request.end_time:
                continue
            matched.append(event)
        return tuple(matched)

    def _build_samples(
        self,
        events: Sequence[StoredEvent],
        sample_size: int,
    ) -> tuple[AnalysisEventSample, ...]:
        sampled = deterministic_sample(events, max_samples=sample_size)
        return tuple(
            AnalysisEventSample(
                event_id=event.id,
                timestamp=event.timestamp,
                severity=event.event.severity,
                source_type=event.event.source_type,
                event_type=get_event_type(event),
                message_preview=(
                    bounded_preview(event.event.message, limit=200)
                    or "[empty after sanitization]"
                ),
                service=get_service(event),
                host=get_host(event),
                parser_name=get_parser_name(event),
            )
            for event in sampled
        )

    @staticmethod
    def _collect_warnings(*results: object | None) -> tuple[str, ...]:
        warnings: list[str] = []
        for result in results:
            if result is None:
                continue
            result_warnings = getattr(result, "warnings", ())
            if isinstance(result_warnings, tuple):
                warnings.extend(
                    warning
                    for warning in result_warnings
                    if isinstance(warning, str) and warning.strip()
                )
        return tuple(dict.fromkeys(warnings))


def analyze_store(
    store: EventStore,
    request: AnalysisRequest,
    *,
    engine: StatisticalAnalysisEngine | None = None,
) -> AnalysisResult:
    """Analyze a lock-free immutable snapshot obtained from an event store."""
    snapshot = store.snapshot_events()
    return (engine or StatisticalAnalysisEngine()).analyze(snapshot, request)
