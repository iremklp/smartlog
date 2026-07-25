"""HTTP API layer for the log parser engine."""

from .app import create_app

__all__ = ["create_app"]