"""Public preview formatting facade for py-lib-runtime.

Why:
    Keeps caller-facing preview helper signatures separate from private
    formatting mechanics.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from py_lib_runtime._internal import (
    preview_exception_message as _preview_exception_message,
    preview_mapping as _preview_mapping,
    preview_text as _preview_text,
    preview_value as _preview_value,
)


def preview_text(value: str, *, max_chars: int = 160) -> str:
    """Return a single-line bounded preview for text values."""
    return _preview_text(value, max_chars=max_chars)


def preview_value(value: object, *, max_chars: int = 160) -> str:
    """Return a bounded preview for an arbitrary value."""
    return _preview_value(value, max_chars=max_chars)


def preview_mapping(
    mapping: Mapping[str, Any],
    *,
    max_items: int = 4,
    value_max_chars: int = 40,
) -> str:
    """Return a bounded preview for a small mapping."""
    return _preview_mapping(
        mapping,
        max_items=max_items,
        value_max_chars=value_max_chars,
    )


def preview_exception_message(
    exc: BaseException,
    *,
    max_chars: int = 160,
) -> str:
    """Return a bounded message preview for an exception."""
    return _preview_exception_message(exc, max_chars=max_chars)
