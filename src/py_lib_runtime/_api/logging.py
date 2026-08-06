"""Public logging facade for py-lib-runtime.

Why:
    Keeps caller-facing logging signatures separate from private structlog and
    stdlib setup mechanics.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from typing import Any

from py_lib_runtime._api.config import LoggingSettings
from py_lib_runtime._api.types import BoundLogger, RetryState
from py_lib_runtime._internal import (
    OperationDurationLogger as _OperationDurationLogger,
    add_library_null_handler as _add_library_null_handler,
    build_logging_settings as _build_logging_settings,
    build_retry_before_sleep_logger as _build_retry_before_sleep_logger,
    configure_logging as _configure_logging,
    configure_package_logging as _configure_package_logging,
    configure_structlog_for_library as _configure_structlog_for_library,
    get_logger as _get_logger,
    log_operation_duration as _log_operation_duration,
    log_retry_exhausted as _log_retry_exhausted,
    set_module_log_levels as _set_module_log_levels,
)

# ================================================================================
# Type Facades
# ================================================================================

OperationDurationLogger = _OperationDurationLogger

# ================================================================================
# Logging Setup
# ================================================================================


def build_logging_settings(
    package_name: str,
    *,
    env_prefix: str | None = None,
    default_local_level: int | str | None = None,
    quiet_module_names: Iterable[str] | None = None,
) -> LoggingSettings:
    """Build project logging settings from a top-level package name."""
    return _build_logging_settings(
        package_name,
        env_prefix=env_prefix,
        default_local_level=default_local_level,
        quiet_module_names=quiet_module_names,
    )


def configure_package_logging(
    package_name: str,
    *,
    env_prefix: str | None = None,
    level: int | str | None = None,
    json: bool | None = None,
    default_local_level: int | str | None = None,
) -> LoggingSettings:
    """Configure stdlib and structlog logging for one package setup."""
    return _configure_package_logging(
        package_name,
        env_prefix=env_prefix,
        level=level,
        json=json,
        default_local_level=default_local_level,
    )


def configure_logging(
    settings: LoggingSettings,
    *,
    level: int | str | None = None,
    json: bool | None = None,
) -> None:
    """Configure structlog and stdlib logging for local runs."""
    _configure_logging(settings, level=level, json=json)


def add_library_null_handler(package_name: str) -> None:
    """Attach a stdlib null handler for a library package namespace."""
    _add_library_null_handler(package_name)


def configure_structlog_for_library() -> None:
    """Route default structlog logging through stdlib without adding handlers."""
    _configure_structlog_for_library()


# ================================================================================
# Logger Access
# ================================================================================


def get_logger(name: str | None = None) -> BoundLogger:
    """Return a structlog logger for the given name."""
    return _get_logger(name)


# ================================================================================
# Operation Timing
# ================================================================================


def log_operation_duration(
    logger: BoundLogger,
    *,
    event_type: str,
    message: str = "Operation completed",
    level: int = logging.DEBUG,
    **fields: object,
) -> OperationDurationLogger:
    """Build a duration logger usable as a context manager or decorator."""
    return _log_operation_duration(
        logger,
        event_type=event_type,
        message=message,
        level=level,
        **fields,
    )


# ================================================================================
# Retry Logging
# ================================================================================


def build_retry_before_sleep_logger(
    logger: BoundLogger,
    *,
    settings: LoggingSettings | None = None,
    event_type: str | None = None,
    context_getter: Callable[[], dict[str, Any]] | None = None,
    state_sink: Callable[[dict[str, Any]], None] | None = None,
) -> Callable[[RetryState], None]:
    """Build a structured retry `before_sleep` callback."""
    return _build_retry_before_sleep_logger(
        logger,
        settings=settings,
        event_type=event_type,
        context_getter=context_getter,
        state_sink=state_sink,
    )


def log_retry_exhausted(
    logger: BoundLogger,
    *,
    error: BaseException,
    settings: LoggingSettings | None = None,
    event_type: str | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """Emit a structured retry exhaustion event."""
    _log_retry_exhausted(
        logger,
        error=error,
        settings=settings,
        event_type=event_type,
        context=context,
    )


# ================================================================================
# Module Levels
# ================================================================================


def set_module_log_levels(level_map: dict[str, int | str]) -> None:
    """Apply custom log levels to specific stdlib loggers."""
    _set_module_log_levels(level_map)
