# py-lib-runtime

Small runtime helpers shared by generated py-lib libraries.

Package docs: [docs/py_lib_runtime/README.md](docs/py_lib_runtime/README.md).

Keep this package narrow. It is for stable runtime behavior that belongs in
installed libraries, not for development checks, scripts, test fixtures, or
project-specific domain code.

Package-root verification:

```bash
uv run ruff format --check src tests examples
uv run ruff check src tests examples
uv run pyright --project pyproject.toml
uv run pytest
uv build --out-dir "${TMPDIR:-/tmp}/py-lib-runtime-build"
```

Current public helpers:

- persistent cache helpers from `py_lib_runtime` with the `cache` extra
- `BaseCacheManager`
- `BoundLogger`
- `CacheConfig`
- `CacheEvents`
- `CacheStats`
- `InvalidCacheNamespaceError`
- `LoggingSettings`
- `OperationDurationLogger`
- `PyLibRuntimeConfig`
- `PyLibRuntimeError`
- `RetryState`
- `RuntimeCacheError`
- `RuntimeConfigError`
- `add_library_null_handler`
- `build_logging_settings`
- `build_retry_before_sleep_logger`
- `cache_from_self_attr`
- `cached`
- `configure_logging`
- `configure_package_logging`
- `configure_structlog_for_library`
- `get_env_cache_dir`
- `get_config`
- `get_logger`
- `install_config`
- `log_operation_duration`
- `log_retry_exhausted`
- `preview_text`
- `preview_value`
- `preview_mapping`
- `preview_exception_message`
- `resolve_cache_dir`
- `set_module_log_levels`
- `validate_non_negative_int`
- `validate_positive_float`
- `validate_positive_int`
