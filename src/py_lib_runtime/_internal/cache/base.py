"""Base persistent cache manager implementation."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import math
import zlib
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping, Sequence, Set
from contextlib import suppress
from datetime import UTC, datetime
from inspect import isawaitable
from pathlib import Path
from typing import Any, TypeVar, cast

from py_lib_runtime._api.defaults import DEFAULT_CACHE_COMPRESSION_THRESHOLD_BYTES
from py_lib_runtime._api.types import CacheStats
from py_lib_runtime._internal.config import get_config
from py_lib_runtime._internal.logging import get_logger
from py_lib_runtime._internal.previews import (
    preview_exception_message,
    preview_value,
)

logger = get_logger(__name__)

T = TypeVar("T")
_CachePayload = dict[str, object]
type _DiskCacheClass = Any
type _DiskCacheLock = Any


# ================================================================================
# Cache Manager
# ================================================================================


class BaseCacheManager[T](ABC):
    """Abstract key-addressed cache manager backed by diskcache."""

    def __init__(
        self,
        cache_dir: Path,
        *,
        max_size: int | None = None,
        compression_threshold: int | None = DEFAULT_CACHE_COMPRESSION_THRESHOLD_BYTES,
        ttl_seconds: float | None = None,
    ) -> None:
        """Initialize a persistent cache manager."""
        resolved_max_size = (
            get_config().cache_max_size_bytes if max_size is None else max_size
        )
        _validate_positive_number(resolved_max_size, name="max_size")
        if compression_threshold is not None:
            _validate_positive_number(
                compression_threshold,
                name="compression_threshold",
            )
        if ttl_seconds is not None:
            _validate_positive_number(ttl_seconds, name="ttl_seconds")

        self._cache_dir = cache_dir
        self._cache: Any | None = None
        self._max_size = resolved_max_size
        self._compression_threshold = compression_threshold
        self._ttl_seconds = ttl_seconds
        self._compression_stats = {
            "compressed_entries": 0,
            "compressed_bytes_in": 0,
            "compressed_bytes_out": 0,
        }
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
        }

        cache_class, _ = _load_diskcache()
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = cache_class(str(self._cache_dir), size_limit=resolved_max_size)
        logger.debug(
            "Cache initialized",
            event_type="py_lib_runtime.cache.lifecycle.initialized",
            cache_dir=str(self._cache_dir),
        )

    def __enter__(self) -> BaseCacheManager[T]:
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        _ = args
        self.close()

    def __del__(self) -> None:
        """Best-effort cleanup for abandoned cache managers."""
        with suppress(Exception):
            self.close()

    def delete(self, key: str, params: Mapping[str, Any] | None = None) -> bool:
        """Remove a cached entry for a key."""
        if self._cache is None:
            return False

        storage_key = self._storage_key(key, params)
        return bool(self._cache.delete(storage_key))

    def get(self, key: str, params: Mapping[str, Any] | None = None) -> T | None:
        """Retrieve a cached entry for a key."""
        if self._cache is None:
            return None

        storage_key = self._storage_key(key, params)
        data = self._cache.get(storage_key)

        if data is None:
            self._cache_stats["misses"] += 1
            return None

        if not isinstance(data, dict):
            self._cache_stats["hits"] += 1
            return cast("T", data)

        self._cache_stats["hits"] += 1
        payload = cast("_CachePayload", data)
        return self._deserialize_entry(self._restore_from_storage(payload), key)

    def set(
        self,
        key: str,
        entry: T,
        params: Mapping[str, Any] | None = None,
    ) -> None:
        """Store an entry in the cache."""
        if self._cache is None:
            return

        storage_key = self._storage_key(key, params)
        data = self._serialize_entry(entry)

        if "timestamp" not in data or data["timestamp"] is None:
            data["timestamp"] = datetime.now(UTC).isoformat()

        self._cache.set(
            storage_key,
            self._prepare_for_storage(data),
            expire=self._ttl_seconds,
        )
        logger.debug(
            "Cached entry stored",
            event_type="py_lib_runtime.cache.entry.stored",
            key_preview=preview_value(key),
        )

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], T],
        params: Mapping[str, Any] | None = None,
        *,
        is_valid: Callable[[T], bool] | None = None,
    ) -> tuple[T, bool]:
        """Atomically get a cached entry or compute and store it."""
        if self._cache is None:
            return factory(), False

        storage_key = self._storage_key(key, params)

        entry, hit = self._get_cached_entry(storage_key, key, is_valid)
        if hit:
            self._cache_stats["hits"] += 1
            return cast("T", entry), True

        with self._lock(storage_key):
            entry, hit = self._get_cached_entry(storage_key, key, is_valid)
            if hit:
                self._cache_stats["hits"] += 1
                return cast("T", entry), True

            entry = factory()
            if entry is None:
                self._cache_stats["misses"] += 1
                return entry, False

            self.set(key, entry, params)
            self._cache_stats["misses"] += 1
            return entry, False

    async def get_or_set_async(
        self,
        key: str,
        factory: Callable[[], Awaitable[T] | T],
        params: Mapping[str, Any] | None = None,
        *,
        is_valid: Callable[[T], bool] | None = None,
    ) -> tuple[T, bool]:
        """Async variant of `get_or_set` for async factories."""
        if self._cache is None:
            entry = factory()
            if isawaitable(entry):
                return cast("T", await entry), False
            return cast("T", entry), False

        storage_key = self._storage_key(key, params)

        entry, hit = self._get_cached_entry(storage_key, key, is_valid)
        if hit:
            self._cache_stats["hits"] += 1
            return cast("T", entry), True

        lock = await self._acquire_lock_async(storage_key)
        try:
            entry, hit = self._get_cached_entry(storage_key, key, is_valid)
            if hit:
                self._cache_stats["hits"] += 1
                return cast("T", entry), True

            entry = factory()
            if isawaitable(entry):
                entry = await cast("Awaitable[T]", entry)
            if entry is None:
                self._cache_stats["misses"] += 1
                return cast("T", entry), False

            self.set(key, cast("T", entry), params)
            self._cache_stats["misses"] += 1
            return cast("T", entry), False
        finally:
            await asyncio.to_thread(lock.release)

    def has(self, key: str, params: Mapping[str, Any] | None = None) -> bool:
        """Return whether a key has a cached entry."""
        if self._cache is None:
            return False

        storage_key = self._storage_key(key, params)
        return storage_key in self._cache

    def clear(self) -> None:
        """Clear all cached entries."""
        if self._cache is not None:
            self._cache.clear()
            logger.info(
                "Cache cleared",
                event_type="py_lib_runtime.cache.lifecycle.cleared",
            )

    def stats(self) -> CacheStats:
        """Return cache statistics."""
        stats = CacheStats(
            enabled=self._cache is not None,
            directory=str(self._cache_dir),
            size_bytes=0,
            entry_count=0,
            cache_hits=self._cache_stats["hits"],
            cache_misses=self._cache_stats["misses"],
            ttl_enabled=self._ttl_seconds is not None,
            ttl_seconds=self._ttl_seconds,
            compression_enabled=self._compression_threshold is not None,
            compression_threshold_bytes=self._compression_threshold,
            compressed_entries=self._compression_stats["compressed_entries"],
            compressed_bytes_in=self._compression_stats["compressed_bytes_in"],
            compressed_bytes_out=self._compression_stats["compressed_bytes_out"],
            compression_savings_bytes=(
                self._compression_stats["compressed_bytes_in"]
                - self._compression_stats["compressed_bytes_out"]
            ),
        )
        if self._cache is None:
            return stats

        stats["size_bytes"] = self._cache.volume()
        stats["entry_count"] = len(self._cache)
        stats["max_size_bytes"] = self._max_size
        return stats

    def close(self) -> None:
        """Close the cache connection."""
        if self._cache is not None:
            self._cache.close()
            self._cache = None
            logger.debug(
                "Cache closed",
                event_type="py_lib_runtime.cache.lifecycle.closed",
            )

    @abstractmethod
    def _serialize_entry(self, entry: T) -> _CachePayload:
        """Convert one cache entry into a storage payload."""

    @abstractmethod
    def _deserialize_entry(self, data: _CachePayload, key: str, /) -> T:
        """Reconstruct one cache entry from a storage payload."""

    def _compress_value(self, value: object) -> tuple[object, int, int, bool]:
        """Compress large string or bytes values for storage."""
        if self._compression_threshold is None:
            return value, 0, 0, False

        raw: bytes | None = None
        encoding: str | None = None

        if isinstance(value, str):
            raw = value.encode("utf-8")
            encoding = "utf-8"
        elif isinstance(value, bytes | bytearray | memoryview):
            raw = bytes(value)

        if raw is None or len(raw) < self._compression_threshold:
            return value, 0, 0, False

        compressed = zlib.compress(raw)
        if len(compressed) >= len(raw):
            return value, 0, 0, False

        wrapped = {
            "__compressed__": True,
            "compression": "zlib",
            "encoding": encoding,
            "data": base64.b64encode(compressed).decode("ascii"),
            "size": len(raw),
        }
        return wrapped, len(raw), len(compressed), True

    def _decompress_value(self, value: object) -> object:
        """Restore a compressed value if it matches the cache wrapper."""
        if not isinstance(value, dict) or not value.get("__compressed__"):
            return value

        try:
            data_b64 = value.get("data")
            if not isinstance(data_b64, str):
                return value
            compressed = base64.b64decode(data_b64)
            raw = zlib.decompress(compressed)
            encoding = value.get("encoding")
            if isinstance(encoding, str):
                return raw.decode(encoding)
        except Exception as exc:
            logger.warning(
                "Failed to decompress cached value; using raw value",
                event_type="py_lib_runtime.cache.compression.restore_failed",
                error_type=type(exc).__name__,
                error_message=preview_exception_message(exc),
            )
            return value
        return raw

    def _prepare_for_storage(self, data: _CachePayload) -> _CachePayload:
        """Compress eligible values before storage."""
        prepared: _CachePayload = {}
        for key, value in data.items():
            compressed_value, raw_size, compressed_size, used = self._compress_value(
                value
            )
            if used:
                self._compression_stats["compressed_entries"] += 1
                self._compression_stats["compressed_bytes_in"] += raw_size
                self._compression_stats["compressed_bytes_out"] += compressed_size
            prepared[key] = compressed_value
        return prepared

    def _restore_from_storage(self, data: _CachePayload) -> _CachePayload:
        """Decompress values restored from storage."""
        return {key: self._decompress_value(value) for key, value in data.items()}

    def _storage_key(self, key: str, params: Mapping[str, Any] | None = None) -> str:
        """Generate a stable storage key from a caller key and parameters."""
        payload = [
            "py-lib-runtime-cache-key-v1",
            _normalize_key_value(key),
            _normalize_key_value(params or None),
        ]
        encoded = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _entry_from_data(self, data: object, key: str) -> T:
        """Normalize cached data into an entry instance."""
        if not isinstance(data, dict):
            return cast("T", data)
        payload = cast("_CachePayload", data)
        return self._deserialize_entry(self._restore_from_storage(payload), key)

    def _get_cached_entry(
        self,
        storage_key: str,
        key: str,
        is_valid: Callable[[T], bool] | None,
    ) -> tuple[T | None, bool]:
        """Resolve a cached entry and validate it if requested."""
        if self._cache is None:
            return None, False
        data = self._cache.get(storage_key)
        if data is None:
            return None, False
        entry = self._entry_from_data(data, key)
        if is_valid is None or is_valid(entry):
            return entry, True
        return None, False

    def _lock(self, key: str) -> _DiskCacheLock:
        """Return a per-key cache lock."""
        if self._cache is None:
            msg = "Cache is not initialized"
            raise RuntimeError(msg)
        lock_key = f"__lock__:{key}"
        if hasattr(self._cache, "lock"):
            lock_method = cast("Callable[[str], _DiskCacheLock]", self._cache.lock)
            return lock_method(lock_key)
        _, lock_class = _load_diskcache()
        return lock_class(self._cache, lock_key)

    async def _acquire_lock_async(self, key: str) -> _DiskCacheLock:
        """Acquire a diskcache lock without blocking the event loop."""
        lock = self._lock(key)
        await asyncio.to_thread(lock.acquire)
        return lock


# ================================================================================
# Key And Option Helpers
# ================================================================================


def _validate_positive_number(value: int | float, *, name: str) -> None:
    """Validate numeric cache configuration."""
    if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        msg = f"{name} must be greater than zero."
        raise ValueError(msg)


def _load_diskcache() -> tuple[_DiskCacheClass, type[_DiskCacheLock]]:
    """Return diskcache primitives or a clear optional-extra error."""
    try:
        from diskcache import Cache, Lock
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised by packaging.
        msg = "Install py-lib-runtime[cache] to use runtime cache helpers."
        raise ModuleNotFoundError(msg) from exc
    return Cache, Lock


def _normalize_key_value(value: object) -> object:
    """Return a JSON-stable, type-tagged cache-key value."""
    scalar_value = _normalize_scalar_key_value(value)
    if scalar_value is not None:
        return scalar_value
    return _normalize_collection_key_value(value)


def _normalize_scalar_key_value(value: object) -> object | None:
    """Return a normalized scalar cache-key value, if supported."""
    if value is None:
        return ["none", None]

    simple_tag = _simple_scalar_tag(value)
    if simple_tag is not None:
        return [simple_tag, value]

    if isinstance(value, float):
        if not math.isfinite(value):
            msg = "Cache key values must not contain non-finite floats."
            raise ValueError(msg)
        return ["float", value]
    if isinstance(value, bytes | bytearray | memoryview):
        return ["bytes", base64.b64encode(bytes(value)).decode("ascii")]
    if isinstance(value, Path):
        return ["path", str(value)]
    return None


def _simple_scalar_tag(value: object) -> str | None:
    """Return the cache-key tag for directly serializable scalar values."""
    for expected_type, tag in ((bool, "bool"), (int, "int"), (str, "str")):
        if isinstance(value, expected_type):
            return tag
    return None


def _normalize_collection_key_value(value: object) -> object:
    """Return a normalized collection cache-key value."""
    if isinstance(value, Mapping):
        items = [
            [_normalize_key_value(item_key), _normalize_key_value(item_value)]
            for item_key, item_value in value.items()
        ]
        return ["mapping", sorted(items, key=_stable_json_sort_key)]
    if isinstance(value, Set):
        items = [_normalize_key_value(item) for item in value]
        return ["set", sorted(items, key=_stable_json_sort_key)]
    if isinstance(value, Sequence):
        return ["sequence", [_normalize_key_value(item) for item in value]]
    msg = f"Unsupported cache key value type: {type(value).__name__}"
    raise TypeError(msg)


def _stable_json_sort_key(value: object) -> str:
    """Return a deterministic sort key for normalized cache-key values."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
