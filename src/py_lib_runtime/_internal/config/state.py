"""Runtime config snapshot state.

Why:
    Keeps process-wide config construction and install/read helpers inside the
    private config implementation.
"""

from __future__ import annotations

from threading import RLock

from py_lib_runtime._internal.config.assembly import build_default_config
from py_lib_runtime._internal.config.models import PyLibRuntimeConfig
from py_lib_runtime._internal.config.validation import validate_config

_installed_config: PyLibRuntimeConfig = build_default_config()
_config_lock = RLock()


def get_config(
    config: PyLibRuntimeConfig | None = None,
) -> PyLibRuntimeConfig:
    """Return a validated runtime configuration snapshot."""
    if config is not None:
        return config
    with _config_lock:
        return _installed_config


def install_config(config: object) -> PyLibRuntimeConfig:
    """Install a validated runtime configuration snapshot."""
    if not isinstance(config, PyLibRuntimeConfig):
        msg = "install_config() expects a PyLibRuntimeConfig instance."
        raise TypeError(msg)

    validate_config(config)
    global _installed_config  # noqa: PLW0603
    with _config_lock:
        _installed_config = config
    return config
