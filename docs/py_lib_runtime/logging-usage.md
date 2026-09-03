---
name: logging-usage
doc_type: usage
description: Structlog and stdlib logging helpers exported by py_lib_runtime.
---

# 1 Logging

## 1.1 Overview

`logging` gives generated libraries one shared structlog/stdlib setup.

Use it for package logging setup in local diagnostic scripts, safe library loggers, duration events, and tenacity-style retry events.

## 1.2 Features

- Provides a unified `configure_package_logging` for standalone diagnostic scripts.
- Derives log levels and JSON formatting toggles automatically from environment variables.
- Exports a safe `get_logger()` that routes default structlog output through stdlib and adds a null handler.
- Provides a context manager for tracking operation durations (`duration_ms`).
- Provides pre-built `tenacity` callbacks for retry sleep and exhaustion events.

## 1.3 Examples

### 1.3.1 Setting Up Package Logging

For local diagnostic scripts where the library acts as the main application.

```python
from py_lib_runtime import configure_package_logging

# Uses SAMPLE_LIB_LOG_LEVEL and SAMPLE_LIB_LOG_JSON automatically
configure_package_logging("sample_lib")

# Or with a custom prefix:
# configure_package_logging("sample_lib", env_prefix="CUSTOM_LIB")
```

### 1.3.2 Using the Library Logger

```python
from py_lib_runtime import get_logger

logger = get_logger(__name__)
logger.info("Loaded item", event_type="sample_lib.item.loaded", item_id="123")
```

### 1.3.3 Tracking Duration Events

Use the context manager to automatically emit a completion log with `duration_ms`.

```python
from py_lib_runtime import get_logger, log_operation_duration

logger = get_logger(__name__)

with log_operation_duration(
    logger,
    event_type="sample_lib.operation.completed",
    operation="fetch",
):
    # Long running work
    pass
```

### 1.3.4 Logging Tenacity Retries

Automatically emit structured retry attempt and exhaustion logs, including attempt number, wait seconds, max attempts, and bounded error messages.

```python
from py_lib_runtime import (
    build_retry_before_sleep_logger,
    get_logger,
    log_retry_exhausted,
)
import tenacity

logger = get_logger(__name__)


@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    before_sleep=build_retry_before_sleep_logger(logger),
)
def run():
    try:
        # Failing work
        pass
    except RuntimeError as exc:
        log_retry_exhausted(logger, error=exc)
        raise
```

## 1.4 Runnable Examples

- [logging_demo.py](../../examples/py_lib_runtime/logging_demo.py)
  Run with: `uv run python examples/py_lib_runtime/logging_demo.py`
