"""Public exceptions for py-lib-runtime.

Why:
    Keeps caller-facing failure types separate from private runtime details.
"""

from __future__ import annotations

from reprlib import repr as bounded_repr

# ================================================================================
# Base Error
# ================================================================================


class PyLibRuntimeError(Exception):
    """Base class for py-lib-runtime public errors."""


# ================================================================================
# Config Errors
# ================================================================================


class RuntimeConfigError(PyLibRuntimeError, ValueError):
    """Raised when runtime configuration cannot be accepted."""


# ================================================================================
# Cache Errors
# ================================================================================


class RuntimeCacheError(PyLibRuntimeError):
    """Raised when runtime cache operations fail at a public boundary."""


class InvalidCacheNamespaceError(RuntimeCacheError, ValueError):
    """Raised when a cache namespace escapes the shared cache root."""

    def __init__(self, *, namespace: str | object) -> None:
        """Build a caller-safe cache namespace validation message."""
        self.namespace = namespace
        super().__init__(f"Invalid cache namespace: {bounded_repr(namespace)}.")
