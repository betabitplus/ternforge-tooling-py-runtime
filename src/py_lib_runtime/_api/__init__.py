"""Public facade package for py-lib-runtime.

Why:
    Groups caller-facing facade modules behind the supported root package
    import boundary.

What belongs here:
    Thin public facades, declarations, and re-export maps consumed by
    `py_lib_runtime.__init__`.

What does not belong here:
    Private runtime mechanics, storage implementations, or mutable config
    state.
"""

from __future__ import annotations
