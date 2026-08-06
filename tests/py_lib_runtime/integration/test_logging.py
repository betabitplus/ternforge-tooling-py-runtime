"""Structured logging public helper tests.

Why:
    Protects logging setup, retry events, duration events, and null-handler
    behavior exposed by the shared runtime logging boundary.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import cast

import pytest
import structlog

from py_lib_runtime import (
    BoundLogger,
    LoggingSettings,
    RetryState,
    add_library_null_handler,
    build_logging_settings,
    build_retry_before_sleep_logger,
    configure_logging,
    configure_package_logging,
    get_logger,
    log_operation_duration,
    log_retry_exhausted,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def restore_logging_state() -> Iterator[None]:
    """Restore global logging state after each logging test."""
    root = logging.getLogger()
    original_root_handlers = root.handlers[:]
    original_root_level = root.level
    watched_loggers = [
        logging.getLogger("sample_lib"),
        logging.getLogger("asyncio"),
        logging.getLogger("httpx"),
        logging.getLogger("noisy_client"),
        logging.getLogger("tenacity"),
        logging.getLogger("urllib3"),
    ]
    original_logger_state = {
        logger.name: (logger.level, logger.handlers[:]) for logger in watched_loggers
    }

    yield

    root.handlers[:] = original_root_handlers
    root.setLevel(original_root_level)
    for logger in watched_loggers:
        level, handlers = original_logger_state[logger.name]
        logger.setLevel(level)
        logger.handlers[:] = handlers
    structlog.reset_defaults()


# =============================================================================
# Helpers
# =============================================================================


class RecordingLogger:
    def __init__(self) -> None:
        self.events: list[tuple[int | str, str, dict[str, object]]] = []

    def log(self, level: int, message: str, **fields: object) -> None:
        self.events.append((level, message, fields))

    def warning(self, message: str, **fields: object) -> None:
        self.events.append(("warning", message, fields))


@dataclass
class NextAction:
    sleep: float


class Stop:
    max_attempt_number = 3


@dataclass
class RetryObject:
    stop: object = field(default_factory=Stop)


@dataclass
class Outcome:
    error: BaseException | None

    def exception(self) -> BaseException | None:
        return self.error


@dataclass
class FakeRetryState:
    attempt_number: int
    next_action: NextAction | None
    outcome: Outcome | None
    retry_object: RetryObject = field(default_factory=RetryObject)


def _settings() -> LoggingSettings:
    return build_logging_settings("sample_lib")


# =============================================================================
# Tests
# =============================================================================


def test_build_logging_settings_derives_project_names() -> None:
    settings = build_logging_settings("sample_lib")

    assert settings.package_name == "sample_lib"
    assert settings.resolved_env_prefix == "SAMPLE_LIB"
    assert settings.env_level == "SAMPLE_LIB_LOG_LEVEL"
    assert settings.env_json == "SAMPLE_LIB_LOG_JSON"
    assert settings.scheduled_retry_event_type == "sample_lib.operation.retry.scheduled"
    assert settings.exhausted_retry_event_type == "sample_lib.operation.retry.exhausted"


def test_configure_logging_uses_project_env_and_module_levels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logging.getLogger().handlers.clear()
    monkeypatch.setenv("SAMPLE_LIB_LOG_LEVEL", "ERROR")

    configure_logging(_settings(), json=True)

    assert len(logging.getLogger().handlers) == 1
    assert logging.getLogger().level == logging.WARNING
    assert logging.getLogger("sample_lib").level == logging.ERROR
    assert logging.getLogger("httpx").level == logging.WARNING


def test_configure_package_logging_uses_static_project_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logging.getLogger().handlers.clear()
    monkeypatch.setenv("CUSTOM_LIB_LOG_LEVEL", "WARNING")

    settings = configure_package_logging(
        "sample_lib",
        env_prefix="CUSTOM_LIB",
    )

    assert settings.env_level == "CUSTOM_LIB_LOG_LEVEL"
    assert logging.getLogger("sample_lib").level == logging.WARNING
    assert any(
        isinstance(handler, logging.NullHandler)
        for handler in logging.getLogger("sample_lib").handlers
    )


def test_get_logger_routes_default_structlog_through_stdlib() -> None:
    structlog.reset_defaults()
    logging.getLogger("sample_lib").handlers.clear()

    logger = get_logger("sample_lib.worker")

    assert hasattr(logger, "bind")
    assert type(structlog.get_config()["logger_factory"]).__name__ == "LoggerFactory"
    assert any(
        isinstance(handler, logging.NullHandler)
        for handler in logging.getLogger("sample_lib").handlers
    )


def test_add_library_null_handler_marks_library_namespace_handled() -> None:
    package_logger = logging.getLogger("sample_lib")
    package_logger.handlers.clear()

    add_library_null_handler("sample_lib")

    assert any(
        isinstance(handler, logging.NullHandler) for handler in package_logger.handlers
    )


def test_log_operation_duration_emits_timing_event() -> None:
    recording_logger = RecordingLogger()

    with log_operation_duration(
        cast("BoundLogger", recording_logger),
        event_type="sample_lib.operation.completed",
        message="Operation completed",
        operation="demo",
    ):
        pass

    assert len(recording_logger.events) == 1
    level, message, fields = recording_logger.events[0]
    assert level == logging.DEBUG
    assert message == "Operation completed"
    assert fields["event_type"] == "sample_lib.operation.completed"
    assert fields["operation"] == "demo"
    assert isinstance(fields["duration_ms"], int)


def test_retry_before_sleep_logger_emits_project_event_and_snapshot() -> None:
    recording_logger = RecordingLogger()
    snapshots: list[dict[str, object]] = []
    callback = build_retry_before_sleep_logger(
        cast("BoundLogger", recording_logger),
        settings=_settings(),
        context_getter=lambda: {"correlation_id": "abc"},
        state_sink=snapshots.append,
    )

    callback(
        cast(
            "RetryState",
            FakeRetryState(
                attempt_number=2,
                next_action=NextAction(sleep=1.5),
                outcome=Outcome(ValueError("  wait\nlater  ")),
            ),
        )
    )

    assert snapshots == [{"attempt_number": 2, "wait_seconds": 1.5, "max_attempts": 3}]
    assert len(recording_logger.events) == 1
    level, message, fields = recording_logger.events[0]
    assert level == "warning"
    assert message == "Operation retry scheduled"
    assert fields == {
        "event_type": "sample_lib.operation.retry.scheduled",
        "attempt_number": 2,
        "wait_seconds": 1.5,
        "max_attempts": 3,
        "error_type": "ValueError",
        "error_message": "wait later",
        "correlation_id": "abc",
    }


def test_log_retry_exhausted_emits_project_event() -> None:
    recording_logger = RecordingLogger()

    log_retry_exhausted(
        cast("BoundLogger", recording_logger),
        error=RuntimeError("  done\nnow  "),
        settings=_settings(),
        context={"attempt_number": 3},
    )

    assert recording_logger.events == [
        (
            "warning",
            "Operation retry exhausted",
            {
                "event_type": "sample_lib.operation.retry.exhausted",
                "error_type": "RuntimeError",
                "error_message": "done now",
                "attempt_number": 3,
            },
        )
    ]
