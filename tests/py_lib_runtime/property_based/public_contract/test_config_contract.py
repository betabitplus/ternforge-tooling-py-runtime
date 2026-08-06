"""Public runtime config property tests.

Why:
    Protects the public config contract with property-based routing in the same
    tree shape used by generated py libraries.

Covers:
    Area: public config lifecycle
    Behavior: repeated public config reads
    Interface: top-level `get_config()`

Checks:
    If generated inputs do not install a new runtime config, then public config
    reads keep returning the same installed snapshot.
"""

from __future__ import annotations

from hypothesis import given, strategies as st

from py_lib_runtime import get_config

# =============================================================================
# Properties
# =============================================================================


@given(st.none())
def test_public_config_snapshot_is_stable(value: None) -> None:
    """Hypothesis inputs do not change public config identity."""
    _ = value

    first = get_config()
    second = get_config()

    assert second is first
