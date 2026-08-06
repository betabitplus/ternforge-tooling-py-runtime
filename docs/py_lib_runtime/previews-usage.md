---
name: previews-usage
doc_type: usage
description: Caller-safe bounded preview helpers exported by py_lib_runtime.
---

# 1 Previews

## 1.1 Overview

`previews` turns values into short, single-line strings for logs and public
errors.

Use previews when logging user data, request params, or exception messages where
full values may be too long or noisy.

## 1.2 Features

- Collapses whitespace and newlines into single spaces.
- Limits output length to prevent massive log payloads.
- Returns `<empty>` for completely blank text.
- Extracts clean strings from exceptions safely, defaulting to the exception type if the message is empty.
- Catches broken `repr()` implementations automatically and returns `<TypeName>`.

## 1.3 Examples

### 1.3.1 Previewing Text and Bytes

Use when logging potentially long or multiline string and byte values.

```python
from py_lib_runtime import preview_text, preview_value

preview_text("  hello\nworld  ")
# "hello world"

preview_value(b"hello\nworld")
# "hello world"
```

### 1.3.2 Previewing Mappings

Use for dictionaries to avoid logging massive nested payloads, bounding the number of items.

```python
from py_lib_runtime import preview_mapping

preview_mapping({"a": "alpha beta", "b": "bravo"}, max_items=1)
# "{a=alpha beta, ...}"
```

### 1.3.3 Previewing Exceptions

Use to safely extract a concise message from an Exception object without dumping unhandled newlines into a structured log field.

```python
from py_lib_runtime import preview_exception_message

preview_exception_message(ValueError("  bad\nvalue  "))
# "bad value"
```

## 1.4 Runnable Examples

- [previews_demo.py](../../examples/py_lib_runtime/previews_demo.py)
  Run with: `uv run python packages/py-lib-runtime/examples/py_lib_runtime/previews_demo.py`
