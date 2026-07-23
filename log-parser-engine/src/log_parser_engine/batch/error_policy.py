from __future__ import annotations

from dataclasses import dataclass

from .options import BatchParseOptions
from log_parser_engine.exceptions.batch import (
    BatchConsecutiveErrorLimitExceeded,
    BatchErrorLimitExceeded,
    BatchErrorRateExceeded,
)
from log_parser_engine.models import BatchItemResult


@dataclass(frozen=True, slots=True)
class StopDecision:
    stop: bool
    reason: str | None = None
    exception_type: type[Exception] | None = None


class ErrorPolicyEvaluator:
    """Evaluate centralized batch stop policies."""

    def __init__(self, options: BatchParseOptions) -> None:
        self._options = options
        self.total_attempted = 0
        self.total_errors = 0
        self.consecutive_errors = 0

    def evaluate_after_result(self, result: BatchItemResult) -> StopDecision:
        if result.status not in {"success", "failure"}:
            return StopDecision(stop=False)

        self.total_attempted += 1
        if result.status == "failure":
            self.total_errors += 1
            self.consecutive_errors += 1

            if self._options.stop_on_error:
                return StopDecision(stop=True, reason="stop_on_error")

            if (
                self._options.max_errors is not None
                and self.total_errors >= self._options.max_errors
            ):
                return StopDecision(
                    stop=True,
                    reason="max_errors",
                    exception_type=BatchErrorLimitExceeded,
                )

            if (
                self._options.max_consecutive_errors is not None
                and self.consecutive_errors >= self._options.max_consecutive_errors
            ):
                return StopDecision(
                    stop=True,
                    reason="max_consecutive_errors",
                    exception_type=BatchConsecutiveErrorLimitExceeded,
                )

            if (
                self._options.error_rate_threshold is not None
                and self.total_attempted >= self._options.error_rate_minimum_records
            ):
                rate = self.total_errors / self.total_attempted
                if rate > self._options.error_rate_threshold:
                    return StopDecision(
                        stop=True,
                        reason="error_rate_threshold",
                        exception_type=BatchErrorRateExceeded,
                    )
        else:
            self.consecutive_errors = 0

        return StopDecision(stop=False)
