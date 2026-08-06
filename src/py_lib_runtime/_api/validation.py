"""Public validation facade for py-lib-runtime.

Why:
    Keeps caller-facing validation helpers separate from private validation
    mechanics.
"""

from __future__ import annotations

from py_lib_runtime._internal import (
    validate_non_negative_int as _validate_non_negative_int,
    validate_positive_float as _validate_positive_float,
    validate_positive_int as _validate_positive_int,
)


def validate_positive_int(*, field_name: str, value: object) -> int:
    """Return a positive integer config value."""
    return _validate_positive_int(field_name=field_name, value=value)


def validate_non_negative_int(*, field_name: str, value: object) -> int:
    """Return a non-negative integer config value."""
    return _validate_non_negative_int(field_name=field_name, value=value)


def validate_positive_float(*, field_name: str, value: object) -> float:
    """Return a positive numeric config value as a float."""
    return _validate_positive_float(field_name=field_name, value=value)
