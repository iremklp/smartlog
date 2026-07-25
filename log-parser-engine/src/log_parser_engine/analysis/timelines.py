from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from log_parser_engine.exceptions.analysis import (
    AnalysisNumericValueError,
    AnalysisTimelineLimitError,
)
from log_parser_engine.models.analysis_request import AnalysisRequest
from log_parser_engine.models.enums import LogSeverity
from log_parser_engine.models.stored_event import StoredEvent
from log_parser_engine.models.timeline import TimelineBucket, TimelineResult

from .extractors import extract_duration_ms, get_http_status, get_severity
from .helpers import epoch_aligned_start, safe_mean, safe_ratio, utc_datetime
from .options import AnalysisOptions
from .percentiles import calculate_percentile
from .sampling import BoundedDeterministicSample
from .validation import validate_stored_events

ALLOWED_BUCKET_SECONDS = (
    1,
    5,
    10,
    30,
    60,
    300,
    900,
    1_800,
    3_600,
    21_600,
    43_200,
    86_400,
)


@dataclass(slots=True)
class _BucketAccumulator:
    event_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    critical_count: int = 0
    status_5xx_count: int = 0
    duration_total: float = 0.0
    duration_count: int = 0
    durations: BoundedDeterministicSample[float] | None = field(
        default=None,
        repr=False,
    )


def _ceil_bucket_end(value: datetime, bucket_seconds: int) -> datetime:
    aligned = _aligned_start(value, bucket_seconds)
    if aligned == utc_datetime(value):
        return aligned
    try:
        return aligned + timedelta(seconds=bucket_seconds)
    except OverflowError as exc:
        raise AnalysisTimelineLimitError(
            "timeline range exceeds supported datetime bounds"
        ) from exc


def _aligned_start(value: datetime, bucket_seconds: int) -> datetime:
    try:
        return epoch_aligned_start(value, bucket_seconds)
    except (OSError, OverflowError, ValueError) as exc:
        raise AnalysisTimelineLimitError(
            "timeline range exceeds supported datetime bounds"
        ) from exc


def _exclusive_event_end(value: datetime) -> datetime:
    try:
        return value + timedelta(microseconds=1)
    except OverflowError as exc:
        raise AnalysisTimelineLimitError(
            "timeline range exceeds supported datetime bounds"
        ) from exc


def _bucket_count(start: datetime, end: datetime, bucket_seconds: int) -> int:
    if end <= start:
        return 0
    return math.ceil((end - start).total_seconds() / bucket_seconds)


def _select_bucket_seconds(
    start: datetime,
    end: datetime,
    *,
    requested: int | None,
    options: AnalysisOptions,
) -> tuple[int, tuple[str, ...]]:
    bucket_seconds = requested or options.default_time_bucket_seconds
    count = _bucket_count(start, end, bucket_seconds)
    if count <= options.max_timeline_buckets:
        return bucket_seconds, ()
    if requested is not None:
        raise AnalysisTimelineLimitError(
            f"timeline bucket count {count} exceeds limit "
            f"{options.max_timeline_buckets}"
        )
    for candidate in ALLOWED_BUCKET_SECONDS:
        if candidate < bucket_seconds:
            continue
        candidate_start = _aligned_start(start, candidate)
        candidate_end = _ceil_bucket_end(end, candidate)
        if (
            _bucket_count(candidate_start, candidate_end, candidate)
            <= options.max_timeline_buckets
        ):
            return candidate, ("TIME_BUCKET_ADJUSTED",)
    raise AnalysisTimelineLimitError(
        "timeline range cannot fit the configured bucket limit"
    )


def build_timeline(
    events: Sequence[StoredEvent],
    request: AnalysisRequest,
    *,
    options: AnalysisOptions | None = None,
    event_predicate: Callable[[StoredEvent], bool] | None = None,
) -> TimelineResult:
    """Build epoch-aligned fixed-width buckets in chronological order."""
    resolved_options = options or AnalysisOptions()
    validate_stored_events(events)
    if (
        request.time_bucket_seconds is not None
        and request.time_bucket_seconds > resolved_options.max_time_bucket_seconds
    ):
        raise AnalysisTimelineLimitError(
            "timeline bucket size exceeds the configured limit"
        )

    def is_eligible(event: StoredEvent) -> bool:
        return (
            (event_predicate is None or event_predicate(event))
            and (
                request.start_time is None
                or event.timestamp >= request.start_time
            )
            and (
                request.end_time is None
                or event.timestamp < request.end_time
            )
        )

    earliest: datetime | None = None
    latest: datetime | None = None
    for event in events:
        if not is_eligible(event):
            continue
        earliest = (
            event.timestamp
            if earliest is None
            else min(earliest, event.timestamp)
        )
        latest = (
            event.timestamp
            if latest is None
            else max(latest, event.timestamp)
        )

    if earliest is not None and latest is not None:
        raw_start = request.start_time or earliest
        raw_end = request.end_time or _exclusive_event_end(latest)
    elif request.start_time is not None and request.end_time is not None:
        raw_start = request.start_time
        raw_end = request.end_time
    else:
        return TimelineResult(
            bucket_seconds=(
                request.time_bucket_seconds
                or resolved_options.default_time_bucket_seconds
            )
        )

    initial_bucket = (
        request.time_bucket_seconds
        or resolved_options.default_time_bucket_seconds
    )
    initial_start = _aligned_start(raw_start, initial_bucket)
    initial_end = _ceil_bucket_end(raw_end, initial_bucket)
    bucket_seconds, warnings = _select_bucket_seconds(
        initial_start,
        initial_end,
        requested=request.time_bucket_seconds,
        options=resolved_options,
    )
    start = _aligned_start(raw_start, bucket_seconds)
    end = _ceil_bucket_end(raw_end, bucket_seconds)
    count = _bucket_count(start, end, bucket_seconds)
    accumulators = [_BucketAccumulator() for _ in range(count)]

    for event in events:
        if not is_eligible(event):
            continue
        timestamp = utc_datetime(event.timestamp)
        index = int((timestamp - start).total_seconds() // bucket_seconds)
        if index < 0 or index >= count:
            continue
        accumulator = accumulators[index]
        accumulator.event_count += 1
        severity = get_severity(event)
        if severity == LogSeverity.WARNING:
            accumulator.warning_count += 1
        elif severity == LogSeverity.ERROR:
            accumulator.error_count += 1
        elif severity in (LogSeverity.CRITICAL, LogSeverity.FATAL):
            accumulator.critical_count += 1

        status = get_http_status(
            event,
            explicit_field=request.status_field,
            candidates=resolved_options.http_status_field_candidates,
            max_depth=resolved_options.max_attribute_depth,
        )
        if status is not None and 500 <= status <= 599:
            accumulator.status_5xx_count += 1

        extracted = extract_duration_ms(
            event,
            explicit_field=request.duration_field,
            candidates=resolved_options.duration_field_candidates,
            max_depth=resolved_options.max_attribute_depth,
            strict=resolved_options.strict_numeric_values,
        )
        if (
            extracted.found
            and not extracted.valid
            and not resolved_options.ignore_non_finite_values
        ):
            raise AnalysisNumericValueError(
                "duration field contains an invalid numeric value"
            )
        if extracted.valid and extracted.value is not None:
            accumulator.duration_total += extracted.value
            accumulator.duration_count += 1
            if accumulator.durations is None:
                accumulator.durations = BoundedDeterministicSample(
                    max_samples=resolved_options.max_percentile_samples,
                    allow_sampling=resolved_options.allow_percentile_sampling,
                )
            accumulator.durations.add(
                extracted.value,
                key=f"{event.content_hash}:{event.id}:{event.sequence}",
            )

    buckets: list[TimelineBucket] = []
    for index, accumulator in enumerate(accumulators):
        bucket_start = start + timedelta(seconds=index * bucket_seconds)
        duration_values = (
            accumulator.durations.values()
            if accumulator.durations is not None
            else ()
        )
        if (
            accumulator.durations is not None
            and accumulator.durations.sampled
        ):
            warnings = tuple((*warnings, "PERCENTILE_SAMPLED"))
        buckets.append(
            TimelineBucket(
                start=bucket_start,
                end=bucket_start + timedelta(seconds=bucket_seconds),
                event_count=accumulator.event_count,
                warning_count=accumulator.warning_count,
                error_count=accumulator.error_count,
                critical_count=accumulator.critical_count,
                error_rate=safe_ratio(
                    accumulator.error_count + accumulator.critical_count,
                    accumulator.event_count,
                ),
                average_duration_ms=safe_mean(
                    accumulator.duration_total,
                    accumulator.duration_count,
                ),
                p95_duration_ms=calculate_percentile(
                    duration_values,
                    95,
                    method=resolved_options.percentile_method,
                ),
                status_5xx_count=accumulator.status_5xx_count,
            )
        )

    max_count = max((bucket.event_count for bucket in buckets), default=0)
    peak = (
        next(
            (bucket.start for bucket in buckets if bucket.event_count == max_count),
            None,
        )
        if max_count > 0
        else None
    )
    return TimelineResult(
        bucket_seconds=bucket_seconds,
        start=start,
        end=end,
        buckets=tuple(buckets),
        empty_bucket_count=sum(bucket.event_count == 0 for bucket in buckets),
        max_bucket_event_count=max_count,
        average_bucket_event_count=(
            sum(bucket.event_count for bucket in buckets) / len(buckets)
            if buckets
            else 0.0
        ),
        peak_bucket_start=peak,
        warnings=tuple(dict.fromkeys(warnings)),
    )
