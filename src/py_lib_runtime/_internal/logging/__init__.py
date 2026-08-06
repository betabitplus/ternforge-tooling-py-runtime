"""Runtime logging implementation package.

Why:
    Exposes the private logging service through a package-shaped internal
    boundary.
"""

from __future__ import annotations

from py_lib_runtime._internal.logging.service import (
    OperationDurationLogger as OperationDurationLogger,
    add_library_null_handler as add_library_null_handler,
    build_logging_settings as build_logging_settings,
    build_retry_before_sleep_logger as build_retry_before_sleep_logger,
    configure_logging as configure_logging,
    configure_package_logging as configure_package_logging,
    configure_structlog_for_library as configure_structlog_for_library,
    get_logger as get_logger,
    log_operation_duration as log_operation_duration,
    log_retry_exhausted as log_retry_exhausted,
    set_module_log_levels as set_module_log_levels,
)
