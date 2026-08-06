"""Cache directory resolution helpers."""

from __future__ import annotations

import os
from pathlib import Path

from py_lib_runtime._internal.config import get_config


def get_env_cache_dir() -> Path | None:
    """Return the cache root declared by `CACHE_DIR`, if any."""
    value = os.getenv(get_config().cache_env_var)
    if not value:
        return None
    return Path(value).expanduser()


def resolve_cache_dir(
    cache_dir: str | Path | None,
    *,
    namespace: str | Path,
) -> Path | None:
    """Resolve a scoped cache directory from an explicit path or env root."""
    if cache_dir is not None:
        return Path(cache_dir).expanduser()

    root = get_env_cache_dir()
    if root is None:
        return None

    namespace_path = Path(namespace)
    if namespace_path.is_absolute() or ".." in namespace_path.parts:
        msg = f"Invalid cache namespace: {namespace!s}"
        raise ValueError(msg)

    return root / namespace_path
