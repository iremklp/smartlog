"""Deterministic statistical analysis over immutable stored event snapshots."""

from .engine import StatisticalAnalysisEngine, analyze_store
from .options import AnalysisOptions

__all__ = [
    "AnalysisOptions",
    "StatisticalAnalysisEngine",
    "analyze_store",
]
