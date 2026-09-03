"""Preview helpers
===============

Runnable examples for the public preview-formatting helpers.
"""

# %%

from __future__ import annotations

from py_lib_runtime import (
    preview_exception_message,
    preview_mapping,
    preview_text,
    preview_value,
)


class BrokenRepr:
    """Object with a broken repr to show caller-safe fallback behavior."""

    def __repr__(self) -> str:
        """Raise like a badly behaved third-party object might."""
        msg = "repr failed"
        raise RuntimeError(msg)


def build_previews() -> dict[str, str]:
    """Return representative preview outputs."""
    return {
        "text": preview_text("  hello\nworld  "),
        "blank": preview_text(" \n\t "),
        "bytes": preview_value(b"hello\nworld"),
        "mapping": preview_mapping(
            {"alpha": "one two three", "bravo": "four"},
            max_items=1,
            value_max_chars=8,
        ),
        "exception": preview_exception_message(ValueError("  bad\nvalue  ")),
        "broken_repr": preview_value(BrokenRepr()),
    }


def main() -> None:
    """Print representative preview outputs."""
    for name, preview in build_previews().items():
        print(f"{name}: {preview}")


if __name__ == "__main__":
    main()
