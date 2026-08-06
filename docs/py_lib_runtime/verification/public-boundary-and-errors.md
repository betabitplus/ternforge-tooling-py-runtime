---
name: py-lib-runtime-public-boundary-verification
doc_type: usage
description: Verification notes for py-lib-runtime public boundary behavior.
---

# Public Boundary And Errors

## Overview

Public-boundary tests ensure callers can rely on the root `py_lib_runtime`
imports without reaching into `_api` or `_internal`.

## Checks

- Root package exports remain present and unique.
- Private implementation imports stay behind approved boundaries.
- Public config and error flows work through root imports.
