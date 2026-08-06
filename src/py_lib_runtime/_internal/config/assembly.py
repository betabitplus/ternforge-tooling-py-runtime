"""Built-in config assembly.

Why:
    Converts public default declarations into validated private config
    snapshots before runtime work begins.
"""

from __future__ import annotations

from py_lib_runtime._api import defaults as api_defaults
from py_lib_runtime._internal.config.models import PyLibRuntimeConfig
from py_lib_runtime._internal.config.validation import validate_config


def build_default_config() -> PyLibRuntimeConfig:
    """Assemble and validate the built-in runtime config snapshot."""
    config = PyLibRuntimeConfig(
        cache_env_var=api_defaults.DEFAULT_CACHE_ENV_VAR,
        cache_max_size_bytes=api_defaults.DEFAULT_CACHE_MAX_SIZE_BYTES,
        logging_default_local_level=api_defaults.DEFAULT_LOGGING_LOCAL_LEVEL,
        logging_default_third_party_level=(
            api_defaults.DEFAULT_LOGGING_THIRD_PARTY_LEVEL
        ),
        logging_quiet_module_names=api_defaults.DEFAULT_LOGGING_QUIET_MODULE_NAMES,
        logging_retry_scheduled_event_type=(
            api_defaults.DEFAULT_LOGGING_RETRY_SCHEDULED_EVENT_TYPE
        ),
        logging_retry_exhausted_event_type=(
            api_defaults.DEFAULT_LOGGING_RETRY_EXHAUSTED_EVENT_TYPE
        ),
    )
    validate_config(config)
    return config
