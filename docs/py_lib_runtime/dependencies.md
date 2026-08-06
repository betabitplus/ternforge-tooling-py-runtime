---
name: py-lib-runtime-dependencies
doc_type: usage
description: Dependency notes for py-lib-runtime.
---

# Dependencies

## Overview

`py-lib-runtime` keeps runtime dependencies small because generated libraries
install it directly.

## Runtime Dependencies

- `structlog` supports structured logging helpers.
- `diskcache` is optional behind the `cache` extra.

## Development Dependencies

Development dependencies are package-local and support tests, examples, typing,
and linting.
