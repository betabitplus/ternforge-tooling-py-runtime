"""Runtime config validation helpers.

Why:
    Centralizes config normalization and invariant checks before snapshots are
    constructed or installed.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from py_lib_runtime._api.errors import RuntimeConfigError

if TYPE_CHECKING:
    from py_lib_runtime._internal.config.models import (
        CacheConfig,
        CacheEvents,
        LoggingSettings,
        PyLibRuntimeConfig,
    )


def _require(*, condition: bool, message: str) -> None:
    """Raise a public config error when a runtime invariant fails."""
    if not condition:
        raise RuntimeConfigError(message)


def _validate_positive_int(*, field_name: str, value: object) -> None:
    """Validate a positive integer config field."""
    if isinstance(value, bool) or not isinstance(value, int):
        _require(condition=False, message=f"{field_name} must be an integer.")
        return
    _require(
        condition=value > 0,
        message=f"{field_name} must be greater than 0.",
    )


def _validate_level(*, field_name: str, value: object) -> None:
    """Validate a stdlib-compatible logging level."""
    if isinstance(value, bool):
        msg = f"{field_name} must be a logging level."
        raise RuntimeConfigError(msg)
    if isinstance(value, int):
        return
    _require(
        condition=isinstance(value, str)
        and value.upper() in logging.getLevelNamesMapping(),
        message=f"{field_name} must be a valid logging level.",
    )


def _validate_optional_callback(
    *,
    field_name: str,
    value: Callable[[dict[str, Any]], None] | None,
) -> None:
    """Validate an optional cache event callback."""
    _require(
        condition=value is None or callable(value),
        message=f"{field_name} must be callable when provided.",
    )


def _validate_required_arg_name(*, field_name: str, value: object) -> None:
    """Validate a required function-argument config field."""
    _require(
        condition=isinstance(value, str) and bool(value.strip()),
        message=f"{field_name} must be a non-empty string.",
    )


def _validate_optional_arg_name(*, field_name: str, value: object) -> None:
    """Validate an optional function-argument config field."""
    if value is None:
        return
    _require(
        condition=isinstance(value, str) and bool(value.strip()),
        message=f"{field_name} must be a non-empty string when provided.",
    )


def validate_logging_settings(config: LoggingSettings) -> None:
    """Validate one logging settings snapshot."""
    _validate_level(
        field_name="LoggingSettings.default_local_level",
        value=config.default_local_level,
    )
    _validate_level(
        field_name="LoggingSettings.default_third_party_level",
        value=config.default_third_party_level,
    )


def validate_cache_config(config: CacheConfig[object, object]) -> None:
    """Validate one cache decorator config snapshot."""
    _validate_required_arg_name(
        field_name="CacheConfig.key_arg",
        value=config.key_arg,
    )
    _validate_optional_arg_name(
        field_name="CacheConfig.params_arg",
        value=config.params_arg,
    )
    _validate_optional_arg_name(
        field_name="CacheConfig.force_refresh_arg",
        value=config.force_refresh_arg,
    )
    _validate_optional_arg_name(
        field_name="CacheConfig.no_cache_arg",
        value=config.no_cache_arg,
    )


def validate_cache_events(config: CacheEvents) -> None:
    """Validate one cache event callback snapshot."""
    _validate_optional_callback(field_name="CacheEvents.on_hit", value=config.on_hit)
    _validate_optional_callback(field_name="CacheEvents.on_miss", value=config.on_miss)
    _validate_optional_callback(
        field_name="CacheEvents.on_store",
        value=config.on_store,
    )


def validate_config(config: PyLibRuntimeConfig) -> None:
    """Validate one runtime config snapshot."""
    _validate_positive_int(
        field_name="PyLibRuntimeConfig.cache_max_size_bytes",
        value=config.cache_max_size_bytes,
    )
    _validate_level(
        field_name="PyLibRuntimeConfig.logging_default_local_level",
        value=config.logging_default_local_level,
    )
    _validate_level(
        field_name="PyLibRuntimeConfig.logging_default_third_party_level",
        value=config.logging_default_third_party_level,
    )
