"""Runtime validation helper tests.

Why:
    Protects shared positive and non-negative numeric validation helpers used
    by py-lib packages at public construction boundaries.
"""

from __future__ import annotations

import pytest

from py_lib_runtime import (
    validate_non_negative_int,
    validate_positive_float,
    validate_positive_int,
)

POSITIVE_INT_VALUE = 3
NON_NEGATIVE_INT_VALUE = 2
POSITIVE_FLOAT_AS_INT = 2
POSITIVE_FLOAT_VALUE = 0.5


def test_validate_positive_int_returns_valid_value() -> None:
    assert (
        validate_positive_int(field_name="limit", value=POSITIVE_INT_VALUE)
        == POSITIVE_INT_VALUE
    )


def test_validate_positive_int_rejects_bool_and_non_positive_values() -> None:
    with pytest.raises(TypeError, match="limit"):
        validate_positive_int(field_name="limit", value=True)
    with pytest.raises(ValueError, match="limit"):
        validate_positive_int(field_name="limit", value=0)


def test_validate_non_negative_int_returns_valid_value() -> None:
    assert validate_non_negative_int(field_name="offset", value=0) == 0
    assert (
        validate_non_negative_int(field_name="offset", value=NON_NEGATIVE_INT_VALUE)
        == NON_NEGATIVE_INT_VALUE
    )


def test_validate_non_negative_int_rejects_bool_and_negative_values() -> None:
    with pytest.raises(TypeError, match="offset"):
        validate_non_negative_int(field_name="offset", value=False)
    with pytest.raises(ValueError, match="offset"):
        validate_non_negative_int(field_name="offset", value=-1)


def test_validate_positive_float_returns_float() -> None:
    assert validate_positive_float(
        field_name="timeout", value=POSITIVE_FLOAT_AS_INT
    ) == float(POSITIVE_FLOAT_AS_INT)
    assert (
        validate_positive_float(field_name="timeout", value=POSITIVE_FLOAT_VALUE)
        == POSITIVE_FLOAT_VALUE
    )


def test_validate_positive_float_rejects_bool_and_non_positive_values() -> None:
    with pytest.raises(TypeError, match="timeout"):
        validate_positive_float(field_name="timeout", value=True)
    with pytest.raises(ValueError, match="timeout"):
        validate_positive_float(field_name="timeout", value=0.0)
