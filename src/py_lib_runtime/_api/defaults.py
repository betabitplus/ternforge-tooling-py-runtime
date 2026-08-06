"""Built-in default declarations for py-lib-runtime.

Why:
    Keeps shared cache and logging defaults in one declarative place instead
    of scattering them across runtime implementation modules.
"""

from __future__ import annotations

import logging

# ================================================================================
# Cache Defaults
# ================================================================================

DEFAULT_CACHE_ENV_VAR = "CACHE_DIR"
DEFAULT_CACHE_MAX_SIZE_BYTES = 1 * 1024**3
DEFAULT_CACHE_COMPRESSION_THRESHOLD_BYTES = 256 * 1024

# ================================================================================
# Logging Defaults
# ================================================================================

DEFAULT_LOGGING_LOCAL_LEVEL = "DEBUG"
DEFAULT_LOGGING_THIRD_PARTY_LEVEL = logging.WARNING
DEFAULT_LOGGING_QUIET_MODULE_NAMES = (
    "asyncio",
    "httpx",
    "tenacity",
    "urllib3",
)
DEFAULT_LOGGING_RETRY_SCHEDULED_EVENT_TYPE = "runtime.operation.retry.scheduled"
DEFAULT_LOGGING_RETRY_EXHAUSTED_EVENT_TYPE = "runtime.operation.retry.exhausted"
