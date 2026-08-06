"""Persistent cache public helper tests.

Why:
    Protects cache directory resolution, storage behavior, stats, expiration,
    async coalescing, and decorator semantics exposed by `py_lib_runtime`.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

from py_lib_runtime import (
    BaseCacheManager,
    CacheConfig,
    CacheEvents,
    InvalidCacheNamespaceError,
    cache_from_self_attr,
    cached,
    resolve_cache_dir,
)

# =============================================================================
# Scenario
# =============================================================================


KEY = "sample:item"
VALUE = "alpha beta"
COMPRESSIBLE_VALUE = "alpha beta " * 200
EXPECTED_DECORATED_CALLS = 2


# =============================================================================
# Helpers
# =============================================================================


@dataclass(frozen=True)
class CacheEntry:
    key: str
    value: str
    timestamp: str | None = None


class ExampleCache(BaseCacheManager[CacheEntry]):
    def _serialize_entry(self, entry: CacheEntry) -> dict[str, object]:
        return {
            "key": entry.key,
            "value": entry.value,
            "timestamp": entry.timestamp,
        }

    def _deserialize_entry(self, data: dict[str, object], key: str) -> CacheEntry:
        timestamp = data.get("timestamp")
        return CacheEntry(
            key=str(data.get("key", key)),
            value=str(data.get("value", "")),
            timestamp=timestamp if isinstance(timestamp, str) else None,
        )


# =============================================================================
# Tests
# =============================================================================


def test_resolve_cache_dir_uses_explicit_path_before_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "env-cache"))

    assert resolve_cache_dir(tmp_path / "explicit", namespace="sample") == (
        tmp_path / "explicit"
    )
    assert resolve_cache_dir(None, namespace="sample/pages") == (
        tmp_path / "env-cache" / "sample" / "pages"
    )
    with pytest.raises(InvalidCacheNamespaceError, match="Invalid cache namespace"):
        resolve_cache_dir(None, namespace="../outside")


def test_base_cache_manager_persists_entries_and_reports_stats(tmp_path: Path) -> None:
    cache = ExampleCache(tmp_path / "cache", compression_threshold=1)

    cache.set(KEY, CacheEntry(key=KEY, value=COMPRESSIBLE_VALUE))

    assert cache.has(KEY)
    entry = cache.get(KEY)
    assert entry is not None
    assert entry.key == KEY
    assert entry.value == COMPRESSIBLE_VALUE
    assert entry.timestamp is not None
    stats = cache.stats()
    assert stats.get("enabled") is True
    assert stats.get("entry_count") == 1
    assert stats.get("cache_hits") == 1
    assert stats.get("compressed_entries") == 1
    assert stats.get("compression_savings_bytes", 0) > 0

    assert cache.delete(KEY) is True
    assert cache.has(KEY) is False


def test_constructor_rejects_invalid_numeric_options(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="max_size"):
        ExampleCache(tmp_path / "bad-size", max_size=0)

    with pytest.raises(ValueError, match="compression_threshold"):
        ExampleCache(tmp_path / "bad-compression", compression_threshold=0)

    with pytest.raises(ValueError, match="ttl_seconds"):
        ExampleCache(tmp_path / "bad-ttl", ttl_seconds=0)

    with pytest.raises(ValueError, match="ttl_seconds"):
        ExampleCache(tmp_path / "bad-nan-ttl", ttl_seconds=float("nan"))


def test_structured_cache_keys_keep_ambiguous_params_distinct(tmp_path: Path) -> None:
    cache = ExampleCache(tmp_path / "cache")

    cache.set(
        KEY,
        CacheEntry(key=KEY, value="single-param"),
        params={"a": "1&b=2"},
    )
    cache.set(
        KEY,
        CacheEntry(key=KEY, value="two-params"),
        params={"a": "1", "b": "2"},
    )

    single_param = cache.get(KEY, params={"a": "1&b=2"})
    two_params = cache.get(KEY, params={"b": "2", "a": "1"})

    assert single_param is not None
    assert single_param.value == "single-param"
    assert two_params is not None
    assert two_params.value == "two-params"


def test_ttl_expiration_removes_cached_entries(tmp_path: Path) -> None:
    cache = ExampleCache(tmp_path / "cache", ttl_seconds=0.01)

    cache.set(KEY, CacheEntry(key=KEY, value=VALUE))

    time.sleep(0.05)
    assert cache.get(KEY) is None


def test_ttl_keeps_fresh_cached_entries(tmp_path: Path) -> None:
    cache = ExampleCache(tmp_path / "cache", ttl_seconds=60)

    cache.set(KEY, CacheEntry(key=KEY, value=VALUE))

    assert cache.get(KEY) is not None


def test_get_or_set_populates_once_and_reuses_cached_entry(tmp_path: Path) -> None:
    cache = ExampleCache(tmp_path / "cache")
    calls = 0

    def factory() -> CacheEntry:
        nonlocal calls
        calls += 1
        return CacheEntry(key=KEY, value=VALUE)

    first, first_from_cache = cache.get_or_set(KEY, factory)
    second, second_from_cache = cache.get_or_set(KEY, factory)

    assert first.key == second.key
    assert first.value == second.value
    assert first_from_cache is False
    assert second_from_cache is True
    assert calls == 1


def test_get_or_set_async_accepts_async_factories(tmp_path: Path) -> None:
    cache = ExampleCache(tmp_path / "cache")
    calls = 0

    async def factory() -> CacheEntry:
        nonlocal calls
        calls += 1
        return CacheEntry(key=KEY, value=VALUE)

    async def scenario() -> tuple[tuple[CacheEntry, bool], tuple[CacheEntry, bool]]:
        first = await cache.get_or_set_async(KEY, factory)
        second = await cache.get_or_set_async(KEY, factory)
        return first, second

    first, second = asyncio.run(scenario())

    assert first[1] is False
    assert second[1] is True
    assert first[0].key == second[0].key
    assert first[0].value == second[0].value
    assert calls == 1


def test_get_or_set_async_coalesces_concurrent_same_key(tmp_path: Path) -> None:
    cache = ExampleCache(tmp_path / "cache")
    calls = 0

    async def factory() -> CacheEntry:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return CacheEntry(key=KEY, value=VALUE)

    async def scenario() -> list[tuple[CacheEntry, bool]]:
        return await asyncio.wait_for(
            asyncio.gather(
                cache.get_or_set_async(KEY, factory),
                cache.get_or_set_async(KEY, factory),
            ),
            timeout=1.0,
        )

    results = asyncio.run(scenario())

    assert [entry.value for entry, _ in results] == [VALUE, VALUE]
    assert sorted(from_cache for _, from_cache in results) == [False, True]
    assert calls == 1


def test_cached_decorator_handles_hits_misses_and_bypass(tmp_path: Path) -> None:
    cache = ExampleCache(tmp_path / "cache")
    calls = 0
    events: list[str] = []

    @cached(
        lambda _: cache,
        options=CacheConfig(
            no_cache_arg="no_cache",
            to_entry=lambda result, bound: CacheEntry(
                key=str(bound["key"]),
                value=result,
            ),
            from_entry=lambda entry: entry.value,
        ),
        events=CacheEvents(
            on_hit=lambda _: events.append("hit"),
            on_miss=lambda _: events.append("miss"),
            on_store=lambda _: events.append("store"),
        ),
    )
    def fetch(key: str, *, no_cache: bool = False) -> str:
        nonlocal calls
        _ = key, no_cache
        calls += 1
        return VALUE

    assert fetch(KEY) == VALUE
    assert fetch(KEY) == VALUE
    assert fetch(KEY, no_cache=True) == VALUE
    assert events == ["miss", "store", "hit", "miss"]
    assert calls == EXPECTED_DECORATED_CALLS


def test_cached_decorator_emits_store_on_force_refresh(tmp_path: Path) -> None:
    cache = ExampleCache(tmp_path / "cache")
    events: list[str] = []

    @cached(
        lambda _: cache,
        events=CacheEvents(
            on_hit=lambda _: events.append("hit"),
            on_miss=lambda _: events.append("miss"),
            on_store=lambda _: events.append("store"),
        ),
    )
    def fetch(key: str, *, force_refresh: bool = False) -> CacheEntry:
        _ = force_refresh
        return CacheEntry(key=key, value=VALUE)

    assert fetch(KEY).value == VALUE
    assert fetch(KEY, force_refresh=True).value == VALUE
    assert events == ["miss", "store", "miss", "store"]


def test_cached_decorator_supports_async_functions(tmp_path: Path) -> None:
    cache = ExampleCache(tmp_path / "cache")
    calls = 0

    @cached(
        lambda _: cache,
        options=CacheConfig(
            to_entry=lambda result, bound: CacheEntry(
                key=str(bound["key"]),
                value=result,
            ),
            from_entry=lambda entry: entry.value,
        ),
    )
    async def fetch(key: str) -> str:
        nonlocal calls
        _ = key
        calls += 1
        return VALUE

    async def scenario() -> tuple[str, str]:
        return await fetch(KEY), await fetch(KEY)

    first, second = asyncio.run(scenario())

    assert first == second == VALUE
    assert calls == 1


def test_cache_from_self_attr_returns_instance_cache(tmp_path: Path) -> None:
    cache = ExampleCache(tmp_path / "cache")

    class Client:
        def __init__(self) -> None:
            self.cache = cache

    assert cache_from_self_attr("cache")({"self": Client()}) is cache
    assert cache_from_self_attr("cache")({}) is None
