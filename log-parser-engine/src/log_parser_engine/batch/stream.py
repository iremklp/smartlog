from __future__ import annotations

from collections.abc import Iterator
from contextlib import AbstractContextManager
from typing import Callable

from log_parser_engine.models import (
    BatchItemResult,
    BatchParseStatistics,
    ParserSessionInfo,
)


class BatchParseStream(
    Iterator[BatchItemResult], AbstractContextManager["BatchParseStream"]
):
    """Lazy iterator wrapper that exposes live/final stream statistics."""

    def __init__(
        self,
        *,
        iterator_factory: Callable[[], Iterator[BatchItemResult]],
        statistics_getter: Callable[[], BatchParseStatistics],
        sessions_getter: Callable[[], tuple[ParserSessionInfo, ...]],
        warnings_getter: Callable[[], tuple[str, ...]],
        close_callback: Callable[[], None] | None = None,
        stop_reason_getter: Callable[[], str | None] | None = None,
    ) -> None:
        self._iterator_factory = iterator_factory
        self._statistics_getter = statistics_getter
        self._sessions_getter = sessions_getter
        self._warnings_getter = warnings_getter
        self._close_callback = close_callback
        self._stop_reason_getter = stop_reason_getter or (lambda: None)
        self._iterator: Iterator[BatchItemResult] | None = None
        self._closed = False

    def __iter__(self) -> "BatchParseStream":
        return self

    def __next__(self) -> BatchItemResult:
        if self._closed:
            raise StopIteration
        if self._iterator is None:
            self._iterator = self._iterator_factory()
        try:
            return next(self._iterator)
        except StopIteration:
            self.close()
            raise
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._close_callback is not None:
            self._close_callback()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> bool | None:
        self.close()
        return None

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def statistics(self) -> BatchParseStatistics:
        return self._statistics_getter()

    @property
    def sessions(self) -> tuple[ParserSessionInfo, ...]:
        return self._sessions_getter()

    @property
    def warnings(self) -> tuple[str, ...]:
        return self._warnings_getter()

    @property
    def completed(self) -> bool:
        return not self.statistics.stopped_early

    @property
    def stop_reason(self) -> str | None:
        return self._stop_reason_getter()
