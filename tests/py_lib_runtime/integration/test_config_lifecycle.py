"""Runtime config lifecycle tests.

Why:
    Protects the installed runtime config snapshot used by shared logging and
    cache helpers.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import pytest

from py_lib_runtime import (
    BaseCacheManager,
    BoundLogger,
    PyLibRuntimeConfig,
    RetryState,
    RuntimeConfigError,
    build_logging_settings,
    build_retry_before_sleep_logger,
    get_config,
    get_env_cache_dir,
    install_config,
)

CUSTOM_CACHE_MAX_SIZE_BYTES = 4096


@dataclass(frozen=True)
class CacheEntry:
    """Minimal cache entry for runtime config lifecycle tests."""

    value: str


class ExampleCache(BaseCacheManager[CacheEntry]):
    """Concrete cache manager used to inspect installed cache defaults."""

    def _serialize_entry(self, entry: CacheEntry) -> dict[str, object]:
        """Convert one test entry into a storage payload."""
        return {"value": entry.value}

    def _deserialize_entry(self, data: dict[str, object], key: str) -> CacheEntry:
        """Convert one storage payload into a test entry."""
        _ = key
        return CacheEntry(value=str(data.get("value", "")))


@pytest.fixture(autouse=True)
def restore_runtime_config() -> Iterator[None]:
    """Restore installed runtime config after each lifecycle test."""
    original_config = get_config()
    yield
    install_config(original_config)


class RecordingLogger:
    """Minimal logger used to capture retry events."""

    def __init__(self) -> None:
        """Initialize the in-memory event sink."""
        self.events: list[tuple[str, dict[str, object]]] = []

    def warning(self, message: str, **fields: object) -> None:
        """Record one warning event."""
        self.events.append((message, fields))


@dataclass
class NextAction:
    """Retry wait metadata."""

    sleep: float


class Stop:
    """Retry stop metadata."""

    max_attempt_number = 3


@dataclass
class RetryObject:
    """Retry object metadata."""

    stop: object = field(default_factory=Stop)


@dataclass
class Outcome:
    """Retry outcome metadata."""

    error: BaseException | None

    def exception(self) -> BaseException | None:
        """Return the exception captured by the retry attempt."""
        return self.error


@dataclass
class FakeRetryState:
    """Test retry state matching the public retry protocol."""

    attempt_number: int
    next_action: NextAction | None
    outcome: Outcome | None
    retry_object: RetryObject = field(default_factory=RetryObject)


def test_install_config_updates_shared_runtime_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = PyLibRuntimeConfig(
        cache_env_var="CUSTOM_CACHE_DIR",
        cache_max_size_bytes=CUSTOM_CACHE_MAX_SIZE_BYTES,
        logging_default_local_level="WARNING",
        logging_default_third_party_level=logging.ERROR,
        logging_quiet_module_names=("noisy_client", "noisy_client"),
        logging_retry_scheduled_event_type="runtime.custom.retry.scheduled",
        logging_retry_exhausted_event_type="runtime.custom.retry.exhausted",
    )

    installed = install_config(config)
    monkeypatch.setenv("CUSTOM_CACHE_DIR", str(tmp_path / "cache"))
    settings = build_logging_settings("sample_lib")

    assert installed is config
    assert get_config() is config
    assert settings.default_local_level == "WARNING"
    assert settings.default_third_party_level == logging.ERROR
    assert settings.quiet_module_names == ("noisy_client",)
    assert settings.scheduled_retry_event_type == "sample_lib.operation.retry.scheduled"
    assert get_env_cache_dir() == tmp_path / "cache"
    assert (
        ExampleCache(tmp_path / "runtime-cache").stats().get("max_size_bytes")
        == CUSTOM_CACHE_MAX_SIZE_BYTES
    )


def test_installed_config_controls_global_retry_events() -> None:
    config = PyLibRuntimeConfig(
        logging_retry_scheduled_event_type="runtime.custom.retry.scheduled",
    )
    install_config(config)
    recording_logger = RecordingLogger()
    callback = build_retry_before_sleep_logger(cast("BoundLogger", recording_logger))

    callback(
        cast(
            "RetryState",
            FakeRetryState(
                attempt_number=2,
                next_action=NextAction(sleep=1.5),
                outcome=Outcome(ValueError("wait later")),
            ),
        )
    )

    assert recording_logger.events[0][1]["event_type"] == (
        "runtime.custom.retry.scheduled"
    )


def test_runtime_config_rejects_invalid_values() -> None:
    with pytest.raises(RuntimeConfigError, match="cache_max_size_bytes"):
        PyLibRuntimeConfig(cache_max_size_bytes=0)

    with pytest.raises(RuntimeConfigError, match="logging_default_local_level"):
        PyLibRuntimeConfig(logging_default_local_level="LOUD")

    with pytest.raises(
        TypeError,
        match=r"PyLibRuntimeConfig\.logging_quiet_module_names",
    ):
        PyLibRuntimeConfig(
            logging_quiet_module_names=["httpx"],  # type: ignore[arg-type]
        )
