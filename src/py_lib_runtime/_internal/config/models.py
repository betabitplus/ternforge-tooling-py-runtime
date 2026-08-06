"""Runtime configuration models.

Why:
    Defines immutable config objects consumed by private runtime helpers.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from py_lib_runtime._api.defaults import (
    DEFAULT_CACHE_ENV_VAR,
    DEFAULT_CACHE_MAX_SIZE_BYTES,
    DEFAULT_LOGGING_LOCAL_LEVEL,
    DEFAULT_LOGGING_QUIET_MODULE_NAMES,
    DEFAULT_LOGGING_RETRY_EXHAUSTED_EVENT_TYPE,
    DEFAULT_LOGGING_RETRY_SCHEDULED_EVENT_TYPE,
    DEFAULT_LOGGING_THIRD_PARTY_LEVEL,
)
from py_lib_runtime._internal.config.validation import (
    validate_cache_config,
    validate_cache_events,
    validate_config,
    validate_logging_settings,
)


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    """Project-specific logging vocabulary and environment settings."""

    package_name: str
    env_prefix: str | None = None
    default_local_level: int | str = DEFAULT_LOGGING_LOCAL_LEVEL
    default_third_party_level: int = DEFAULT_LOGGING_THIRD_PARTY_LEVEL
    quiet_module_names: tuple[str, ...] = DEFAULT_LOGGING_QUIET_MODULE_NAMES
    retry_scheduled_event_type: str | None = None
    retry_exhausted_event_type: str | None = None

    def __post_init__(self) -> None:
        """Normalize and validate logging settings."""
        object.__setattr__(
            self,
            "package_name",
            _normalize_name("LoggingSettings.package_name", self.package_name),
        )
        if self.env_prefix is not None:
            object.__setattr__(
                self,
                "env_prefix",
                _normalize_name("LoggingSettings.env_prefix", self.env_prefix),
            )
        object.__setattr__(
            self,
            "quiet_module_names",
            _normalize_name_tuple(
                "LoggingSettings.quiet_module_names",
                self.quiet_module_names,
            ),
        )
        validate_logging_settings(self)

    @property
    def env_level(self) -> str:
        """Return the project log-level environment variable name."""
        return f"{self.resolved_env_prefix}_LOG_LEVEL"

    @property
    def env_json(self) -> str:
        """Return the project JSON-logging environment variable name."""
        return f"{self.resolved_env_prefix}_LOG_JSON"

    @property
    def resolved_env_prefix(self) -> str:
        """Return the explicit or package-derived environment prefix."""
        if self.env_prefix is not None:
            return self.env_prefix
        return _derive_env_prefix(self.package_name)

    @property
    def scheduled_retry_event_type(self) -> str:
        """Return the project retry-scheduled event type."""
        return (
            self.retry_scheduled_event_type
            or f"{self.package_name}.operation.retry.scheduled"
        )

    @property
    def exhausted_retry_event_type(self) -> str:
        """Return the project retry-exhausted event type."""
        return (
            self.retry_exhausted_event_type
            or f"{self.package_name}.operation.retry.exhausted"
        )

    def module_levels(self, *, package_level: int) -> dict[str, int]:
        """Return default module log levels for local runs."""
        levels = {self.package_name: package_level}
        levels.update(
            dict.fromkeys(self.quiet_module_names, self.default_third_party_level)
        )
        return levels


@dataclass(frozen=True, slots=True)
class CacheConfig[R, E]:
    """Configuration for `cached`."""

    key_arg: str = "key"
    params_arg: str | None = "params"
    force_refresh_arg: str | None = "force_refresh"
    no_cache_arg: str | None = None
    to_entry: Callable[[R, dict[str, Any]], E] | None = None
    from_entry: Callable[[E], R] | None = None

    def __post_init__(self) -> None:
        """Validate cache decorator option names."""
        validate_cache_config(self)


@dataclass(frozen=True, slots=True)
class CacheEvents:
    """Optional callbacks for cache decorator events."""

    on_hit: Callable[[dict[str, Any]], None] | None = None
    on_miss: Callable[[dict[str, Any]], None] | None = None
    on_store: Callable[[dict[str, Any]], None] | None = None

    def __post_init__(self) -> None:
        """Validate optional cache event callbacks."""
        validate_cache_events(self)


@dataclass(frozen=True, slots=True)
class PyLibRuntimeConfig:
    """Installed defaults for shared py-lib runtime helpers."""

    cache_env_var: str = DEFAULT_CACHE_ENV_VAR
    cache_max_size_bytes: int = DEFAULT_CACHE_MAX_SIZE_BYTES
    logging_default_local_level: int | str = DEFAULT_LOGGING_LOCAL_LEVEL
    logging_default_third_party_level: int = DEFAULT_LOGGING_THIRD_PARTY_LEVEL
    logging_quiet_module_names: tuple[str, ...] = field(
        default_factory=lambda: DEFAULT_LOGGING_QUIET_MODULE_NAMES
    )
    logging_retry_scheduled_event_type: str = DEFAULT_LOGGING_RETRY_SCHEDULED_EVENT_TYPE
    logging_retry_exhausted_event_type: str = DEFAULT_LOGGING_RETRY_EXHAUSTED_EVENT_TYPE

    def __post_init__(self) -> None:
        """Normalize and validate runtime config values."""
        object.__setattr__(
            self,
            "cache_env_var",
            _normalize_name("PyLibRuntimeConfig.cache_env_var", self.cache_env_var),
        )
        object.__setattr__(
            self,
            "logging_quiet_module_names",
            _normalize_name_tuple(
                "PyLibRuntimeConfig.logging_quiet_module_names",
                self.logging_quiet_module_names,
            ),
        )
        object.__setattr__(
            self,
            "logging_retry_scheduled_event_type",
            _normalize_name(
                "PyLibRuntimeConfig.logging_retry_scheduled_event_type",
                self.logging_retry_scheduled_event_type,
            ),
        )
        object.__setattr__(
            self,
            "logging_retry_exhausted_event_type",
            _normalize_name(
                "PyLibRuntimeConfig.logging_retry_exhausted_event_type",
                self.logging_retry_exhausted_event_type,
            ),
        )
        validate_config(self)


def _derive_env_prefix(package_name: str) -> str:
    """Return the py-lib default environment prefix for a package name."""
    return package_name.replace(".", "_").replace("-", "_").upper()


def _normalize_name(field_name: str, value: object) -> str:
    """Return a stripped non-empty string config field."""
    if not isinstance(value, str) or not value.strip():
        msg = f"{field_name} must be a non-empty string."
        raise ValueError(msg)
    return value.strip()


def _normalize_name_tuple(field_name: str, value: object) -> tuple[str, ...]:
    """Return a de-duplicated tuple of non-empty string config fields."""
    if not isinstance(value, tuple):
        msg = f"{field_name} must be a tuple of strings."
        raise TypeError(msg)

    names = [_normalize_name(field_name, item) for item in value]
    return tuple(dict.fromkeys(names))
