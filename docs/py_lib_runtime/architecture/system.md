---
name: py-lib-runtime-system
doc_type: usage
description: System architecture summary for py-lib-runtime.
---

# System

## Overview

`py-lib-runtime` is a narrow installed helper package for generated libraries.
It provides shared runtime behavior such as logging, previews, validation, and
cache helpers.

## Structure

- `src/py_lib_runtime/__init__.py` exposes the supported public API.
- `src/py_lib_runtime/_api/` owns caller-facing facades and declarations.
- `src/py_lib_runtime/_internal/` owns private implementation details.
- `examples/py_lib_runtime/` contains runnable public API reference examples.
- `tests/py_lib_runtime/` protects behavior and public contracts.
