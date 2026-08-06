"""Shared structured logging implementation for py-lib libraries.

Why:
    Keeps structlog setup, duration events, and retry event formatting in one
    installed runtime package while projects supply static logging policy only
    at explicit setup boundaries.
"""

from __future__ import annotations

import functools
import inspect
import logging
import os
import time
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, ParamSpec, TypeVar, cast, overload

import structlog

from py_lib_runtime._api.types import BoundLogger, RetryState
from py_lib_runtime._internal.config import LoggingSettings, get_config
from py_lib_runtime._internal.previews import preview_exception_message

P = ParamSpec("P")
R = TypeVar("R")


# ================================================================================
# Setup API
# ================================================================================


def build_logging_settings(
    package_name: str,
    *,
    env_prefix: str | None = None,
    default_local_level: int | str | None = None,
    quiet_module_names: Iterable[str] | None = None,
) -> LoggingSettings:
    """Build project logging settings from a top-level package name."""
    resolved_package_name = _normalize_package_name(package_name)
    config = get_config()
    return LoggingSettings(
        package_name=resolved_package_name,
        env_prefix=env_prefix,
        default_local_level=(
            config.logging_default_local_level
            if default_local_level is None
            else default_local_level
        ),
        default_third_party_level=config.logging_default_third_party_level,
        quiet_module_names=(
            config.logging_quiet_module_names
            if quiet_module_names is None
            else tuple(dict.fromkeys(quiet_module_names))
        ),
    )


def configure_package_logging(
    package_name: str,
    *,
    env_prefix: str | None = None,
    level: int | str | None = None,
    json: bool | None = None,
    default_local_level: int | str | None = None,
) -> LoggingSettings:
    """Configure stdlib and structlog logging for one explicit package setup."""
    settings = build_logging_settings(
        package_name,
        env_prefix=env_prefix,
        default_local_level=default_local_level,
    )
    configure_logging(settings, level=level, json=json)
    return settings


def add_library_null_handler(package_name: str) -> None:
    """Attach a stdlib null handler for a library package namespace."""
    logger = logging.getLogger(_normalize_package_name(package_name))
    if any(isinstance(handler, logging.NullHandler) for handler in logger.handlers):
        return
    logger.addHandler(logging.NullHandler())


def configure_structlog_for_library() -> None:
    """Route default structlog logging through stdlib without adding handlers."""
    config = structlog.get_config()
    if type(config.get("logger_factory")).__name__ != "PrintLoggerFactory":
        return

    structlog.configure(
        processors=_build_structlog_processors(),
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def configure_logging(
    settings: LoggingSettings,
    *,
    level: int | str | None = None,
    json: bool | None = None,
) -> None:
    """Configure structlog and stdlib logging for local runs."""
    add_library_null_handler(settings.package_name)
    numeric_level = _coerce_level(settings, level)
    want_json = json if json is not None else os.getenv(settings.env_json) == "1"

    root = logging.getLogger()
    if not root.handlers:
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=_build_renderer(want_json=want_json),
            foreign_pre_chain=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
            ],
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)

    root.setLevel(settings.default_third_party_level)

    structlog.configure(
        processors=_build_structlog_processors(),
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    set_module_log_levels(settings.module_levels(package_level=numeric_level))


def get_logger(name: str | None = None) -> BoundLogger:
    """Return a structlog logger for the given name."""
    configure_structlog_for_library()
    if name is not None:
        add_library_null_handler(_derive_package_name(name))
    return cast("BoundLogger", structlog.get_logger(name))


# ================================================================================
# Operation Duration
# ================================================================================


class OperationDurationLogger:
    """Context manager and decorator for operation duration logging."""

    def __init__(
        self,
        logger: BoundLogger,
        *,
        event_type: str,
        message: str,
        level: int,
        fields: dict[str, object],
    ) -> None:
        """Store fixed logging metadata for one operation boundary."""
        self._logger = logger
        self._event_type = event_type
        self._message = message
        self._level = level
        self._fields = fields
        self._start: float | None = None

    def __enter__(self) -> None:
        """Start timing a synchronous code block."""
        self._start = time.perf_counter()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> bool:
        """Emit elapsed duration when a synchronous code block exits."""
        _ = exc_type, exc, traceback
        if self._start is not None:
            self._emit_duration(self._start)
        self._start = None
        return False

    @overload
    def __call__(
        self,
        func: Callable[P, Awaitable[R]],
    ) -> Callable[P, Awaitable[R]]: ...

    @overload
    def __call__(self, func: Callable[P, R]) -> Callable[P, R]: ...

    def __call__(
        self,
        func: Callable[P, R] | Callable[P, Awaitable[R]],
    ) -> Callable[P, R] | Callable[P, Awaitable[R]]:
        """Decorate a sync or async function with duration logging."""
        if inspect.iscoroutinefunction(func):
            async_func = cast("Callable[P, Awaitable[R]]", func)

            @functools.wraps(async_func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                """Execute an async operation and log elapsed duration."""
                start = time.perf_counter()
                try:
                    return await async_func(*args, **kwargs)
                finally:
                    self._emit_duration(start)

            return async_wrapper

        sync_func = cast("Callable[P, R]", func)

        @functools.wraps(sync_func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            """Execute a sync operation and log elapsed duration."""
            start = time.perf_counter()
            try:
                return sync_func(*args, **kwargs)
            finally:
                self._emit_duration(start)

        return sync_wrapper

    def _emit_duration(self, start: float) -> None:
        """Emit one structured duration event."""
        self._logger.log(
            self._level,
            self._message,
            event_type=self._event_type,
            duration_ms=int((time.perf_counter() - start) * 1000),
            **self._fields,
        )


def log_operation_duration(
    logger: BoundLogger,
    *,
    event_type: str,
    message: str = "Operation completed",
    level: int = logging.DEBUG,
    **fields: object,
) -> OperationDurationLogger:
    """Build a duration logger usable as a context manager or decorator."""
    return OperationDurationLogger(
        logger,
        event_type=event_type,
        message=message,
        level=level,
        fields=fields,
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
    retry_event_type = _resolve_retry_event_type(
        settings=settings,
        event_type=event_type,
        event_attr="scheduled_retry_event_type",
    )

    def _callback(retry_state: RetryState) -> None:
        """Log one retry scheduling decision using the shared event schema."""
        event = _build_retry_scheduled_event(
            retry_state,
            event_type=retry_event_type,
        )
        if state_sink is not None:
            state_sink(_build_retry_state_snapshot(event))
        if context_getter is not None:
            event.update(context_getter())

        logger.warning("Operation retry scheduled", **event)

    return _callback


def log_retry_exhausted(
    logger: BoundLogger,
    *,
    error: BaseException,
    settings: LoggingSettings | None = None,
    event_type: str | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """Emit a structured retry exhaustion event."""
    retry_event_type = _resolve_retry_event_type(
        settings=settings,
        event_type=event_type,
        event_attr="exhausted_retry_event_type",
    )
    event: dict[str, Any] = {
        "event_type": retry_event_type,
        "error_type": type(error).__name__,
        "error_message": preview_exception_message(error),
    }
    if context:
        event.update(context)
    logger.warning("Operation retry exhausted", **event)


# ================================================================================
# Module-Level Helpers
# ================================================================================


def set_module_log_levels(level_map: dict[str, int | str]) -> None:
    """Apply custom log levels to specific stdlib loggers."""
    for logger_name, level in level_map.items():
        numeric_level = _resolve_optional_level(level)
        if numeric_level is None:
            continue
        logging.getLogger(logger_name).setLevel(numeric_level)


def _build_structlog_processors() -> list[Callable[..., Any]]:
    """Return the shared processor chain for stdlib-backed structlog logging."""
    return [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]


def _coerce_level(settings: LoggingSettings, level: int | str | None) -> int:
    """Return a stdlib numeric log level from an int, str, or env default."""
    resolved_level = level
    if resolved_level is None:
        resolved_level = os.getenv(settings.env_level, settings.default_local_level)
    if isinstance(resolved_level, int):
        return resolved_level
    return logging.getLevelNamesMapping().get(
        str(resolved_level).upper(),
        logging.INFO,
    )


def _resolve_optional_level(level: int | str) -> int | None:
    """Return a numeric log level or `None` when the input is invalid."""
    if isinstance(level, int):
        return level
    return logging.getLevelNamesMapping().get(level.upper())


def _derive_package_name(module_name: str) -> str:
    """Return a top-level import package name from a module name."""
    normalized = module_name.strip()
    if not normalized:
        msg = "module_name must be a non-empty dotted module path."
        raise ValueError(msg)
    return _normalize_package_name(normalized.split(".", maxsplit=1)[0])


def _normalize_package_name(package_name: str) -> str:
    """Return a stripped package name or raise a clear config error."""
    normalized = package_name.strip()
    if not normalized:
        msg = "package_name must be a non-empty package name."
        raise ValueError(msg)
    return normalized


def _extract_retry_timing(retry_state: RetryState) -> tuple[float | None, int | None]:
    """Return wait and max-attempt metadata from a retry state."""
    next_action = retry_state.next_action
    wait_seconds = None if next_action is None else float(next_action.sleep)
    stop = getattr(retry_state.retry_object, "stop", None)
    max_attempts = getattr(stop, "max_attempt_number", None)
    if not isinstance(max_attempts, int):
        max_attempts = None
    return wait_seconds, max_attempts


def _build_retry_scheduled_event(
    retry_state: RetryState,
    *,
    event_type: str,
) -> dict[str, Any]:
    """Build the structured event payload for a scheduled retry."""
    outcome = retry_state.outcome
    exc = None if outcome is None else outcome.exception()
    wait_seconds, max_attempts = _extract_retry_timing(retry_state)
    event: dict[str, Any] = {
        "event_type": event_type,
        "attempt_number": int(retry_state.attempt_number),
    }
    if wait_seconds is not None:
        event["wait_seconds"] = wait_seconds
    if max_attempts is not None:
        event["max_attempts"] = max_attempts
    if exc is not None:
        event["error_type"] = type(exc).__name__
        event["error_message"] = preview_exception_message(exc)
    return event


def _build_retry_state_snapshot(scheduled_event: dict[str, Any]) -> dict[str, Any]:
    """Return retry timing fields suitable for storing as request context."""
    snapshot = {"attempt_number": scheduled_event["attempt_number"]}
    for key in ("wait_seconds", "max_attempts"):
        value = scheduled_event.get(key)
        if value is not None:
            snapshot[key] = value
    return snapshot


def _resolve_retry_event_type(
    *,
    settings: LoggingSettings | None,
    event_type: str | None,
    event_attr: str,
) -> str:
    """Return the explicit, project-specific, or runtime default event type."""
    if event_type is not None:
        return event_type
    if settings is not None:
        return cast("str", getattr(settings, event_attr))
    config = get_config()
    if event_attr == "scheduled_retry_event_type":
        return config.logging_retry_scheduled_event_type
    if event_attr == "exhausted_retry_event_type":
        return config.logging_retry_exhausted_event_type
    msg = f"Unsupported retry event attribute: {event_attr}"
    raise ValueError(msg)


def _build_renderer(*, want_json: bool) -> Callable[..., Any]:
    """Return the renderer used by the optional default stream handler."""
    if want_json:
        return structlog.processors.JSONRenderer()
    return structlog.dev.ConsoleRenderer()
