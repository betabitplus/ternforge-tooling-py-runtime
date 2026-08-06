# py-lib-runtime Tests

The package-local test tree follows the starter routing shape.

Because this package lives inside a multi-package workspace, test directories
intentionally omit `__init__.py` files so they cannot shadow the shipped
`py_lib_runtime` package during root-level verification.

- `tests/py_lib_runtime/unit/` protects small public helper contracts.
- `tests/py_lib_runtime/integration/` protects runtime behavior that touches
  process logging state, async coordination, filesystem-backed cache storage,
  or third-party runtime helpers.
- `tests/py_lib_runtime/property_based/` is reserved for generated invariants.
- `tests/py_lib_runtime/e2e/` is reserved for executable public scenarios if
  this shared runtime package later needs them.
- `tests/py_lib_runtime/support/` is reserved for package-specific reusable
  test builders or assertions.
