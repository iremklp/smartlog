from __future__ import annotations

from typing import Any

from log_parser_engine.models import JsonProfileDetection

from .constants import SUPPORTED_PROFILES


def detect_profile(data: dict[str, object]) -> JsonProfileDetection:
    if not isinstance(data, dict):
        raise ValueError("data must be a mapping")

    signals: list[str] = []
    matched_paths: list[str] = []
    best_profile = "generic"
    best_confidence = 0.0

    for profile_name in SUPPORTED_PROFILES:
        confidence = 0.0
        profile_signals = []
        for signal in _profile_signals(profile_name):
            if _path_exists(data, signal):
                confidence += 0.25
                profile_signals.append(signal)
        if confidence > best_confidence:
            best_profile = profile_name
            best_confidence = confidence
            signals = profile_signals
            matched_paths = profile_signals

    if best_confidence < 0.5:
        return JsonProfileDetection(
            profile="generic",
            confidence=0.4,
            signals=(),
            matched_paths=(),
            reason="no structured profile matched",
        )
    return JsonProfileDetection(
        profile=best_profile,
        confidence=min(best_confidence, 1.0),
        signals=tuple(signals),
        matched_paths=tuple(matched_paths),
        reason="profile signals matched",
    )


def _profile_signals(profile_name: str) -> tuple[str, ...]:
    from .constants import PROFILE_SIGNAL_FIELDS

    return tuple(PROFILE_SIGNAL_FIELDS.get(profile_name, ()))


def _path_exists(data: dict[str, object], path: str) -> bool:
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False
    return True
