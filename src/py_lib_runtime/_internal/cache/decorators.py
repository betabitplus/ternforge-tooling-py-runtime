"""Decorator utilities for cache-backed functions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from functools import wraps
from inspect import Signature, iscoroutinefunction, signature
from typing import Any, cast, overload

from py_lib_runtime._internal.cache.base import BaseCacheManager
from py_lib_runtime._internal.config import CacheConfig, CacheEvents

# ================================================================================
# Runtime Context
# ================================================================================


@dataclass(frozen=True)
class CacheContext[R, E]:
    """Resolved cache context for one function call."""

    cache: BaseCacheManager[E] | None
    key: str
    params: Mapping[str, Any] | None
    bound: dict[str, Any]
    options: CacheConfig[R, E]
    events: CacheEvents
    force_refresh: bool
    no_cache: bool


# ================================================================================
# Runtime Helpers
# ================================================================================


def _bind_args[**P](
    sig: Signature, *args: P.args, **kwargs: P.kwargs
) -> dict[str, Any]:
    """Bind function arguments to parameter names."""
    bound = sig.bind_partial(*args, **kwargs)
    bound.apply_defaults()
    return dict(bound.arguments)


def _get_key(bound: dict[str, Any], key_arg: str) -> str:
    """Extract the cache key from bound arguments."""
    if key_arg not in bound:
        msg = f"Missing required cache key arg: {key_arg}"
        raise KeyError(msg)
    return cast("str", bound[key_arg])


def _get_params(
    bound: dict[str, Any], params_arg: str | None
) -> Mapping[str, Any] | None:
    """Extract optional cache parameters from bound arguments."""
    if params_arg is None:
        return None
    return cast("Mapping[str, Any] | None", bound.get(params_arg))


def _force_refresh(bound: dict[str, Any], force_refresh_arg: str | None) -> bool:
    """Return whether the call requested a forced refresh."""
    if force_refresh_arg is None:
        return False
    return bool(bound.get(force_refresh_arg, False))


def _no_cache(bound: dict[str, Any], no_cache_arg: str | None) -> bool:
    """Return whether the call should bypass cache reads and writes."""
    if no_cache_arg is None:
        return False
    return bool(bound.get(no_cache_arg, False))


def _emit_hit[R, E](context: CacheContext[R, E]) -> None:
    """Emit a cache hit event if configured."""
    if context.events.on_hit:
        context.events.on_hit(context.bound)


def _emit_miss[R, E](context: CacheContext[R, E]) -> None:
    """Emit a cache miss event if configured."""
    if context.events.on_miss:
        context.events.on_miss(context.bound)


def _emit_store[R, E](context: CacheContext[R, E]) -> None:
    """Emit a cache store event if configured."""
    if context.events.on_store:
        context.events.on_store(context.bound)


def _to_entry[R, E](context: CacheContext[R, E], result: R) -> E:
    """Convert a function result into a cache entry."""
    if context.options.to_entry:
        return context.options.to_entry(result, context.bound)
    return cast("E", result)


def _from_entry[R, E](context: CacheContext[R, E], entry: E) -> R:
    """Convert a cache entry into a function result."""
    if context.options.from_entry:
        return context.options.from_entry(entry)
    return cast("R", entry)


def _store_cache[R, E](context: CacheContext[R, E], result: R) -> bool:
    """Store a result when cache writes are enabled."""
    if context.cache is None or context.no_cache or result is None:
        return False
    entry = _to_entry(context, result)
    context.cache.set(context.key, entry, context.params)
    return True


def _build_context_factory[R, E](
    cache_getter: Callable[[dict[str, Any]], BaseCacheManager[E] | None],
    options: CacheConfig[R, E],
    events: CacheEvents,
) -> Callable[[dict[str, Any]], CacheContext[R, E]]:
    """Create a cache context builder with fixed options and events."""

    def _build_context(bound: dict[str, Any]) -> CacheContext[R, E]:
        """Build cache context from bound arguments."""
        return CacheContext(
            cache=cache_getter(bound),
            key=_get_key(bound, options.key_arg),
            params=_get_params(bound, options.params_arg),
            bound=bound,
            options=options,
            events=events,
            force_refresh=_force_refresh(bound, options.force_refresh_arg),
            no_cache=_no_cache(bound, options.no_cache_arg),
        )

    return _build_context


async def _call_cached_async[**P, R, E](
    func: Callable[P, Awaitable[R]],
    sig: Signature,
    build_context: Callable[[dict[str, Any]], CacheContext[R, E]],
    *args: P.args,
    **kwargs: P.kwargs,
) -> R:
    """Execute an async function with cache resolution."""
    bound = _bind_args(sig, *args, **kwargs)
    context = build_context(bound)

    if context.cache is None or context.force_refresh:
        _emit_miss(context)
        result = await func(*args, **kwargs)
        if _store_cache(context, result):
            _emit_store(context)
        return result

    if context.no_cache:
        _emit_miss(context)
        return await func(*args, **kwargs)

    result_holder: dict[str, R] = {}

    async def _compute_entry() -> E:
        """Compute the entry used to populate the cache."""
        result = await func(*args, **kwargs)
        result_holder["value"] = result
        return _to_entry(context, result)

    entry, from_cache = await context.cache.get_or_set_async(
        context.key,
        _compute_entry,
        context.params,
    )

    if from_cache:
        _emit_hit(context)
        return _from_entry(context, entry)

    _emit_miss(context)
    if entry is not None:
        _emit_store(context)
    return cast("R", result_holder.get("value"))


def _call_cached_sync[**P, R, E](
    func: Callable[P, R],
    sig: Signature,
    build_context: Callable[[dict[str, Any]], CacheContext[R, E]],
    *args: P.args,
    **kwargs: P.kwargs,
) -> R:
    """Execute a sync function with cache resolution."""
    bound = _bind_args(sig, *args, **kwargs)
    context = build_context(bound)

    if context.cache is None or context.force_refresh:
        _emit_miss(context)
        result = func(*args, **kwargs)
        if _store_cache(context, result):
            _emit_store(context)
        return result

    if context.no_cache:
        _emit_miss(context)
        return func(*args, **kwargs)

    result_holder: dict[str, R] = {}

    def _compute_entry() -> E:
        """Compute the entry used to populate the cache."""
        result = func(*args, **kwargs)
        result_holder["value"] = result
        return _to_entry(context, result)

    entry, from_cache = context.cache.get_or_set(
        context.key,
        _compute_entry,
        context.params,
    )

    if from_cache:
        _emit_hit(context)
        return _from_entry(context, entry)

    _emit_miss(context)
    if entry is not None:
        _emit_store(context)
    return cast("R", result_holder.get("value"))


# ================================================================================
# Public Decorator
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

    def decorator(
        func: Callable[P, Any],
    ) -> Callable[P, Any]:
        """Decorate a function to cache its results."""
        sig = signature(func)
        opts = options or CacheConfig()
        callbacks = events or CacheEvents()
        build_context = _build_context_factory(cache_getter, opts, callbacks)

        if iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> object:
                """Async wrapper for a cached function."""
                return await _call_cached_async(
                    cast("Callable[P, Awaitable[object]]", func),
                    sig,
                    cast(
                        "Callable[[dict[str, Any]], CacheContext[object, E]]",
                        build_context,
                    ),
                    *args,
                    **kwargs,
                )

            return cast("Callable[P, Any]", async_wrapper)

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> object:
            """Sync wrapper for a cached function."""
            return _call_cached_sync(
                func,
                sig,
                build_context,
                *args,
                **kwargs,
            )

        return cast("Callable[P, Any]", sync_wrapper)

    return decorator


def cache_from_self_attr(
    attr_name: str,
) -> Callable[[dict[str, Any]], BaseCacheManager[Any] | None]:
    """Create a cache getter for a cache stored on `self`."""

    def _get_cache(bound: dict[str, Any]) -> BaseCacheManager[Any] | None:
        """Extract cache from an instance-bound attribute."""
        instance = bound.get("self")
        if instance is None:
            return None
        return getattr(instance, attr_name, None)

    return _get_cache
