"""Shared validation primitives for runtime config boundaries.

Why:
    Keeps common numeric config checks consistent across py-lib packages while
    allowing product-specific validators to own domain-specific errors.
"""

from __future__ import annotations


def validate_positive_int(*, field_name: str, value: object) -> int:
    """Return a positive integer config value."""
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field_name} must be an integer."
        raise TypeError(msg)
    if value <= 0:
        msg = f"{field_name} must be greater than 0."
        raise ValueError(msg)
    return value


def validate_non_negative_int(*, field_name: str, value: object) -> int:
    """Return a non-negative integer config value."""
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field_name} must be an integer."
        raise TypeError(msg)
    if value < 0:
        msg = f"{field_name} must be greater than or equal to 0."
        raise ValueError(msg)
    return value


def validate_positive_float(*, field_name: str, value: object) -> float:
    """Return a positive numeric config value as a float."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{field_name} must be numeric."
        raise TypeError(msg)
    numeric_value = float(value)
    if numeric_value <= 0.0:
        msg = f"{field_name} must be greater than 0.0."
        raise ValueError(msg)
    return numeric_value
