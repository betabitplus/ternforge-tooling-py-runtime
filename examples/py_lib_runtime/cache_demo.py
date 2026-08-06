# %%
"""Runnable persistent cache helper examples.

Run from the repository root:
    uv run python packages/py-lib-runtime/examples/py_lib_runtime/cache_demo.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from py_lib_runtime import (
    BaseCacheManager,
    CacheConfig,
    CacheEvents,
    cache_from_self_attr,
    cached,
    resolve_cache_dir,
)


@dataclass(frozen=True)
class PageEntry:
    """Typed cache entry stored by the example cache manager."""

    key: str
    html: str
    timestamp: str | None = None


class PageCache(BaseCacheManager[PageEntry]):
    """Persistent cache manager for page entries."""

    def _serialize_entry(self, entry: PageEntry) -> dict[str, object]:
        """Convert one entry into a disk payload."""
        return {
            "key": entry.key,
            "html": entry.html,
            "timestamp": entry.timestamp,
        }

    def _deserialize_entry(self, data: dict[str, object], key: str, /) -> PageEntry:
        """Rebuild one entry from a disk payload."""
        timestamp = data.get("timestamp")
        return PageEntry(
            key=str(data.get("key", key)),
            html=str(data.get("html", "")),
            timestamp=timestamp if isinstance(timestamp, str) else None,
        )


class PageClient:
    """Tiny client that caches public method results."""

    def __init__(self, cache: PageCache) -> None:
        """Store the cache manager used by the decorator."""
        self.page_cache = cache
        self.fetch_calls = 0

    @cached(
        cache_from_self_attr("page_cache"),
        options=CacheConfig(
            no_cache_arg="no_cache",
            to_entry=lambda result, bound: PageEntry(
                key=str(bound["key"]),
                html=result,
            ),
            from_entry=lambda entry: entry.html,
        ),
        events=CacheEvents(
            on_hit=lambda bound: print(f"event: hit {bound['key']}"),
            on_miss=lambda bound: print(f"event: miss {bound['key']}"),
            on_store=lambda bound: print(f"event: store {bound['key']}"),
        ),
    )
    def fetch_page(self, key: str, *, no_cache: bool = False) -> str:
        """Return a page body, caching normal calls by key."""
        _ = no_cache
        self.fetch_calls += 1
        return f"<html><title>{key}</title></html>"


def main() -> None:
    """Resolve a cache dir, store entries, and exercise the decorator."""
    with TemporaryDirectory() as temp_dir:
        cache_root = Path(temp_dir) / "cache-root"
        cache_dir = cast(
            "Path",
            resolve_cache_dir(cache_root, namespace="demo/pages"),
        )

        cache = PageCache(cache_dir, compression_threshold=1)
        entry, first_from_cache = cache.get_or_set(
            "home",
            lambda: PageEntry(key="home", html="<html>home</html>"),
        )
        _, second_from_cache = cache.get_or_set(
            "home",
            lambda: PageEntry(key="home", html="<html>new</html>"),
        )

        client = PageClient(cache)
        first = client.fetch_page("docs")
        second = client.fetch_page("docs")
        bypass = client.fetch_page("docs", no_cache=True)

        stats = cache.stats()
        print(f"resolved_cache_dir: {cache_dir.relative_to(cache_root)}")
        print(f"manual_entry: {entry.key} from_cache={first_from_cache}")
        print(f"manual_second_from_cache: {second_from_cache}")
        print(f"decorated_same_value: {first == second == bypass}")
        print(f"decorated_fetch_calls: {client.fetch_calls}")
        print(f"cache_entries: {stats.get('entry_count')}")


if __name__ == "__main__":
    main()
