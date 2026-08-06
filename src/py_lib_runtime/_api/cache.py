"""Public persistent cache facade for py-lib-runtime.

Why:
    Keeps optional cache helpers behind one caller-facing boundary while
    deferring the `diskcache` extra until cache storage is used.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, cast, overload

from py_lib_runtime._api.config import CacheConfig, CacheEvents
from py_lib_runtime._api.defaults import DEFAULT_CACHE_COMPRESSION_THRESHOLD_BYTES
from py_lib_runtime._api.errors import InvalidCacheNamespaceError
from py_lib_runtime._internal import (
    BaseCacheManager as _InternalBaseCacheManager,
    cache_from_self_attr as _cache_from_self_attr,
    cached as _cached,
    get_env_cache_dir as _get_env_cache_dir,
    resolve_cache_dir as _resolve_cache_dir,
)

# ================================================================================
# Cache Manager Facade
# ================================================================================


class BaseCacheManager[T](_InternalBaseCacheManager[T]):
    """Public base class for typed persistent cache managers."""

    def __init__(
        self,
        cache_dir: str | Path,
        *,
        max_size: int | None = None,
        compression_threshold: int | None = DEFAULT_CACHE_COMPRESSION_THRESHOLD_BYTES,
        ttl_seconds: float | None = None,
    ) -> None:
        """Initialize a persistent cache manager."""
        super().__init__(
            Path(cache_dir),
            max_size=max_size,
            compression_threshold=compression_threshold,
            ttl_seconds=ttl_seconds,
        )


# ================================================================================
# Decorator Facade
# ================================================================================


@overload
def cached[**P, R, E](
    cache_getter: Callable[[dict[str, Any]], BaseCacheManager[E] | None],
    options: CacheConfig[R, E] | None = None,
    events: CacheEvents | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]: ...


@overload
def cached[**P, R, E](  # pyright: ignore[reportOverlappingOverload]
    cache_getter: Callable[[dict[str, Any]], BaseCacheManager[E] | None],
    options: CacheConfig[R, E] | None = None,
    events: CacheEvents | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def cached[**P, R, E](  # pyright: ignore[reportInconsistentOverload]
    cache_getter: Callable[[dict[str, Any]], BaseCacheManager[E] | None],
    options: CacheConfig[R, E] | None = None,
    events: CacheEvents | None = None,
) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    """Cache function results using a `BaseCacheManager`."""
    return _cached(
        cast(
            "Callable[[dict[str, Any]], _InternalBaseCacheManager[E] | None]",
            cache_getter,
        ),
        options=options,
        events=events,
    )


# ================================================================================
# Cache Getter Helpers
# ================================================================================


def cache_from_self_attr(
    attr_name: str,
) -> Callable[[dict[str, Any]], BaseCacheManager[Any] | None]:
    """Create a cache getter for a cache stored on `self`."""
    getter = _cache_from_self_attr(attr_name)

    def _get_cache(bound: dict[str, Any]) -> BaseCacheManager[Any] | None:
        """Extract cache from an instance-bound attribute."""
        return cast("BaseCacheManager[Any] | None", getter(bound))

    return _get_cache


# ================================================================================
# Cache Directory Helpers
# ================================================================================


def get_env_cache_dir() -> Path | None:
    """Return the cache root declared by `CACHE_DIR`, if any."""
    return _get_env_cache_dir()


def resolve_cache_dir(
    cache_dir: str | Path | None,
    *,
    namespace: str | Path,
) -> Path | None:
    """Resolve a scoped cache directory from an explicit path or env root."""
    try:
        return _resolve_cache_dir(cache_dir, namespace=namespace)
    except ValueError as exc:
        if str(exc).startswith("Invalid cache namespace"):
            raise InvalidCacheNamespaceError(namespace=namespace) from exc
        raise
