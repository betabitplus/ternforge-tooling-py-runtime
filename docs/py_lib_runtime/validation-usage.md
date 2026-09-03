---
name: validation-usage
doc_type: usage
description: Numeric validation helpers exported by py_lib_runtime.
---

# 1 Validation

## 1.1 Overview

`validation` contains small numeric validators for public constructors and config
boundaries.

Use these when several libraries need the same error behavior for numeric
options.

## 1.2 Features

- Validates that integers are strictly positive.
- Validates that integers are non-negative.
- Validates that floats are strictly positive.
- Throws consistent exception messages containing the provided `field_name`.

## 1.3 Examples

### 1.3.1 Validating Positive Integers

Use this for limits, sizes, or counts where `0` is invalid.

```python
from py_lib_runtime import validate_positive_int

limit = validate_positive_int(field_name="limit", value=10)
```

### 1.3.2 Validating Non-Negative Integers

Use this for offsets, indexes, or retry counters that are allowed to be `0`.

```python
from py_lib_runtime import validate_non_negative_int

offset = validate_non_negative_int(field_name="offset", value=0)
```

### 1.3.3 Validating Positive Floats

Use this for time durations, delays, timeouts, or fractional limits.

```python
from py_lib_runtime import validate_positive_float

timeout = validate_positive_float(field_name="timeout", value=0.5)
```

## 1.4 Runnable Examples

- [validation_demo.py](../../examples/py_lib_runtime/validation_demo.py)
  Run with: `uv run python examples/py_lib_runtime/validation_demo.py`
