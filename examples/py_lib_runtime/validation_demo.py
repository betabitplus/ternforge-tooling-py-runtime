"""Numeric validation helpers
==========================

Runnable examples for the public numeric-validation helpers.
"""

# %%

from __future__ import annotations

from collections.abc import Callable

from py_lib_runtime import (
    validate_non_negative_int,
    validate_positive_float,
    validate_positive_int,
)


def main() -> None:
    """Validate accepted values and show concise rejection messages."""
    limit = validate_positive_int(field_name="limit", value=10)
    offset = validate_non_negative_int(field_name="offset", value=0)
    timeout = validate_positive_float(field_name="timeout", value=0.5)

    print(f"limit: {limit}")
    print(f"offset: {offset}")
    print(f"timeout: {timeout}")
    _show_rejection(
        "invalid_limit",
        lambda: validate_positive_int(field_name="limit", value=0),
    )
    _show_rejection(
        "invalid_timeout",
        lambda: validate_positive_float(field_name="timeout", value=True),
    )


def _show_rejection(name: str, call: Callable[[], object]) -> None:
    """Print the exception type and message for one rejected value."""
    try:
        call()
    except (TypeError, ValueError) as exc:
        print(f"{name}: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
