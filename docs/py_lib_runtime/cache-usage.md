---
name: cache-usage
doc_type: usage
description: Persistent cache helpers exported by py_lib_runtime.
---

# 1 Cache

## 1.1 Overview

`cache` is for typed persistent get-or-compute around expensive keyed work.

Use it when several libraries need the same pattern:

1. Resolve a stable key and optional params.
2. Read a persistent cache.
3. Compute once on miss.
4. Store a typed entry.
5. Return the typed value.

Use raw `diskcache` when a project only needs simple key/value storage.

## 1.2 Features

- Resolves cache directories consistently using the `CACHE_DIR` environment variable.
- Provides a strongly-typed, persistent `BaseCacheManager` for serialization and deserialization.
- Supports both synchronous and asynchronous compute-on-miss (`get_or_set`).
- Features a `@cached` decorator to easily wrap methods with cache behavior.
- Allows event tracking via `CacheEvents` for hit, miss, and store callbacks.

## 1.3 Examples

### 1.3.1 Resolving Cache Directories

Namespaces must stay relative. Explicit paths win over `CACHE_DIR`.

```python
from py_lib_runtime import resolve_cache_dir

# Uses CACHE_DIR/sample_lib/pages
cache_dir = resolve_cache_dir(None, namespace="sample_lib/pages")

# Uses explicit path, ignoring CACHE_DIR
explicit_dir = resolve_cache_dir("/tmp/sample-cache", namespace="ignored")
```

### 1.3.2 Defining a Typed Cache Manager

Subclass `BaseCacheManager` and define how your entries are serialized to disk.

```python
from dataclasses import dataclass
from py_lib_runtime import BaseCacheManager


@dataclass(frozen=True)
class PageEntry:
    key: str
    html: str


class PageCache(BaseCacheManager[PageEntry]):
    def _serialize_entry(self, entry: PageEntry) -> dict[str, object]:
        return {"key": entry.key, "html": entry.html}

    def _deserialize_entry(self, data: dict[str, object], key: str) -> PageEntry:
        return PageEntry(key=key, html=str(data["html"]))
```

### 1.3.3 Using the Cache Decorator

Use `cached` when a function should read/write through a cache manager automatically.

```python
from py_lib_runtime import CacheConfig, cached


class PageClient:
    def __init__(self, cache: PageCache):
        self.page_cache = cache

    @cached(
        lambda bound: bound["self"].page_cache,
        options=CacheConfig(no_cache_arg="no_cache"),
    )
    def fetch_page(self, key: str, *, no_cache: bool = False) -> str:
        # Expensive work
        return "<html>...</html>"
```

## 1.4 Runnable Examples

- [cache_demo.py](../../examples/py_lib_runtime/cache_demo.py)
  Run with: `uv run python examples/py_lib_runtime/cache_demo.py`
