"""Caller-safe preview helper tests.

Why:
    Protects bounded text, value, mapping, and exception previews used by
    public errors and structured logs.
"""

from __future__ import annotations

from py_lib_runtime import (
    preview_exception_message,
    preview_mapping,
    preview_text,
    preview_value,
)


def test_preview_text_collapses_whitespace_and_limits_width() -> None:
    assert preview_text("  hello\n\nworld  ") == "hello world"
    assert preview_text("alpha beta gamma", max_chars=12) == "alpha..."
    assert preview_text(" \n\t ") == "<empty>"
    assert preview_text(" \n\t ", max_chars=2) == ".."
    assert preview_text("alpha beta", max_chars=2) == ".."


def test_preview_value_handles_bytes_and_bad_repr() -> None:
    class BadRepr:
        def __repr__(self) -> str:
            msg = "boom"
            raise RuntimeError(msg)

    assert preview_value(b"hello\nworld") == "hello world"
    assert preview_value(BadRepr()) == "<BadRepr>"


def test_preview_mapping_limits_items_and_values() -> None:
    preview = preview_mapping(
        {"a": "alpha beta", "b": "bravo", "c": "charlie"},
        max_items=2,
        value_max_chars=8,
    )

    assert preview == "{a=alpha..., b=bravo, ...}"
    assert preview_mapping({"a": "alpha"}, max_items=0) == "{...}"


def test_preview_exception_message_uses_type_for_empty_message() -> None:
    assert preview_exception_message(ValueError()) == "ValueError"
    assert preview_exception_message(ValueError(), max_chars=2) == ".."
    assert preview_exception_message(ValueError("  bad\nvalue  ")) == "bad value"
