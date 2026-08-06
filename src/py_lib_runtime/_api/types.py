"""Public runtime type declarations.

Why:
    Keeps caller-facing logging and cache contracts separate from private
    implementation mechanics.
"""

from __future__ import annotations

from typing import Protocol, TypedDict

# ================================================================================
# Logging Types
# ================================================================================


class BoundLogger(Protocol):
    """Structured logger operations used by py-lib runtime helpers."""

    def bind(self, **new_values: object) -> BoundLogger:
        """Return a logger with additional bound context."""

    def debug(self, event: str, **event_kw: object) -> object:
        """Emit a debug event."""

    def info(self, event: str, **event_kw: object) -> object:
        """Emit an info event."""

    def warning(self, event: str, **event_kw: object) -> object:
        """Emit a warning event."""

    def error(self, event: str, **event_kw: object) -> object:
        """Emit an error event."""

    def log(self, level: int, event: str, **event_kw: object) -> object:
        """Emit an event at the provided stdlib log level."""


# ================================================================================
# Retry Types
# ================================================================================


class _RetryNextAction(Protocol):
    """Structural shape for retry libraries that expose a next wait."""

    sleep: float


class _RetryOutcome(Protocol):
    """Structural shape for retry libraries that expose a final exception."""

    def exception(self) -> BaseException | None:
        """Return the exception captured by the retry attempt."""


class _RetryObject(Protocol):
    """Structural shape for retry libraries that expose stop metadata."""

    stop: object


class RetryState(Protocol):
    """Tenacity-compatible retry state shape used by retry log callbacks."""

    attempt_number: int
    next_action: _RetryNextAction | None
    outcome: _RetryOutcome | None
    retry_object: _RetryObject


# ================================================================================
# Cache Types
# ================================================================================


class CacheStats(TypedDict, total=False):
    """Persistent cache statistics."""

    enabled: bool
    directory: str
    size_bytes: int
    entry_count: int
    max_size_bytes: int
    cache_hits: int
    cache_misses: int
    ttl_enabled: bool
    ttl_seconds: float | None
    compression_enabled: bool
    compression_threshold_bytes: int | None
    compressed_entries: int
    compressed_bytes_in: int
    compressed_bytes_out: int
    compression_savings_bytes: int
