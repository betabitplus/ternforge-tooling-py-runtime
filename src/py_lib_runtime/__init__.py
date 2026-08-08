"""Supported public package entrypoint for py-lib-runtime.

Why:
    Exposes shared py-lib runtime helpers from one stable root import boundary.

What belongs here:
    Caller-safe preview helpers, validation helpers, logging setup helpers,
    cache helper declarations, and package version.

What does not belong here:
    Private implementation modules, storage mechanics, raw defaults, or
    additional public facade modules.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from py_lib_runtime._api.cache import (
    BaseCacheManager,
    cache_from_self_attr,
    cached,
    get_env_cache_dir,
    resolve_cache_dir,
)
from py_lib_runtime._api.config import (
    CacheConfig,
    CacheEvents,
    LoggingSettings,
    PyLibRuntimeConfig,
    get_config,
    install_config,
)
from py_lib_runtime._api.errors import (
    InvalidCacheNamespaceError,
    PyLibRuntimeError,
    RuntimeCacheError,
    RuntimeConfigError,
)
from py_lib_runtime._api.logging import (
    OperationDurationLogger,
    add_library_null_handler,
    build_logging_settings,
    build_retry_before_sleep_logger,
    configure_logging,
    configure_package_logging,
    configure_structlog_for_library,
    get_logger,
    log_operation_duration,
    log_retry_exhausted,
    set_module_log_levels,
)
from py_lib_runtime._api.previews import (
    preview_exception_message,
    preview_mapping,
    preview_text,
    preview_value,
)
from py_lib_runtime._api.types import BoundLogger, CacheStats, RetryState
from py_lib_runtime._api.validation import (
    validate_non_negative_int,
    validate_positive_float,
    validate_positive_int,
)

try:
    __version__ = version("py-lib-runtime")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+local"

__all__ = [
    "BaseCacheManager",
    "BoundLogger",
    "CacheConfig",
    "CacheEvents",
    "CacheStats",
    "InvalidCacheNamespaceError",
    "LoggingSettings",
    "OperationDurationLogger",
    "PyLibRuntimeConfig",
    "PyLibRuntimeError",
    "RetryState",
    "RuntimeCacheError",
    "RuntimeConfigError",
    "__version__",
    "add_library_null_handler",
    "build_logging_settings",
    "build_retry_before_sleep_logger",
    "cache_from_self_attr",
    "cached",
    "configure_logging",
    "configure_package_logging",
    "configure_structlog_for_library",
    "get_config",
    "get_env_cache_dir",
    "get_logger",
    "install_config",
    "log_operation_duration",
    "log_retry_exhausted",
    "preview_exception_message",
    "preview_mapping",
    "preview_text",
    "preview_value",
    "resolve_cache_dir",
    "set_module_log_levels",
    "validate_non_negative_int",
    "validate_positive_float",
    "validate_positive_int",
]
