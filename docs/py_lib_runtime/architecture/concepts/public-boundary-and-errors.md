---
name: py-lib-runtime-public-boundary-and-errors
doc_type: usage
description: Public boundary and error rules for py-lib-runtime.
---

# Public Boundary And Errors

## Overview

`py_lib_runtime` exposes supported helpers from the package root. Private
implementation details stay under `_internal`; caller-facing facades live under
`_api` and are re-exported by `py_lib_runtime`.

## Public Imports

Use root imports in product code and examples.

```python
from py_lib_runtime import get_logger, preview_value
```

## Error Boundary

Runtime-specific errors derive from public package errors and should be raised
through root-exported names when callers need to catch them.
