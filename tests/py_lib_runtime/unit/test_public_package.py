"""Public package boundary tests.

Why:
    Protects the starter-shaped root package layout and optional cache import
    behavior.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import py_lib_runtime

_ALLOWED_INTERNAL_API_MODULE_IMPORTS = frozenset(
    {
        "py_lib_runtime._api.defaults",
        "py_lib_runtime._api.errors",
        "py_lib_runtime._api.types",
    }
)
_ALLOWED_INTERNAL_API_ROOT_IMPORTS = frozenset({"defaults"})


def test_package_root_contains_only_starter_shape_files() -> None:
    package_root = Path(py_lib_runtime.__file__).parent

    root_files = {path.name for path in package_root.iterdir() if path.is_file()}

    assert root_files == {"__init__.py", "py.typed"}


def test_api_package_contains_runtime_facades() -> None:
    package_root = Path(py_lib_runtime.__file__).parent
    api_files = {
        path.name for path in package_root.joinpath("_api").iterdir() if path.is_file()
    }

    assert api_files == {
        "__init__.py",
        "cache.py",
        "config.py",
        "defaults.py",
        "errors.py",
        "logging.py",
        "previews.py",
        "types.py",
        "validation.py",
    }


def test_internal_package_imports_only_api_declarations() -> None:
    package_root = Path(py_lib_runtime.__file__).parent

    for path in package_root.joinpath("_internal").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    _assert_allowed_internal_api_import(alias.name, path)
            if isinstance(node, ast.ImportFrom):
                _assert_allowed_internal_api_import_from(node, path)


def test_root_import_does_not_require_cache_extra() -> None:
    package_root = Path(__file__).parents[3]
    script = textwrap.dedent(
        """
        from __future__ import annotations

        import importlib.abc
        import sys
        from pathlib import Path
        from tempfile import TemporaryDirectory

        class BlockDiskcache(importlib.abc.MetaPathFinder):
            def find_spec(
                self,
                fullname: str,
                path: object | None,
                target: object | None = None,
            ):
                if fullname == "diskcache" or fullname.startswith("diskcache."):
                    raise ModuleNotFoundError("blocked diskcache")
                return None

        sys.modules.pop("diskcache", None)
        sys.meta_path.insert(0, BlockDiskcache())

        import py_lib_runtime
        from py_lib_runtime import get_logger, validate_positive_int

        assert py_lib_runtime.__version__
        assert get_logger is not None
        assert validate_positive_int(field_name="value", value=1) == 1

        from py_lib_runtime import BaseCacheManager

        class ExampleCache(BaseCacheManager[str]):
            def _serialize_entry(self, entry: str) -> dict[str, object]:
                return {"value": entry}

            def _deserialize_entry(
                self,
                data: dict[str, object],
                key: str,
            ) -> str:
                return str(data.get("value", key))

        with TemporaryDirectory() as tmp_dir:
            try:
                ExampleCache(Path(tmp_dir))
            except ModuleNotFoundError as exc:
                assert "py-lib-runtime[cache]" in str(exc)
            else:
                raise AssertionError("cache use should require the cache extra")
        """
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(package_root / "src")
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def _assert_allowed_internal_api_import(module_name: str, path: Path) -> None:
    """Assert private code imports only public declaration modules."""
    if not module_name.startswith("py_lib_runtime._api"):
        return

    assert module_name in _ALLOWED_INTERNAL_API_MODULE_IMPORTS, (
        f"{path} imports facade module {module_name!r}"
    )


def _assert_allowed_internal_api_import_from(
    node: ast.ImportFrom,
    path: Path,
) -> None:
    """Assert private code does not route through public facade modules."""
    module_name = node.module or ""
    if not module_name.startswith("py_lib_runtime._api"):
        return

    if module_name == "py_lib_runtime._api":
        imported_names = {alias.name for alias in node.names}
        assert imported_names <= _ALLOWED_INTERNAL_API_ROOT_IMPORTS, (
            f"{path} imports facade names from {module_name!r}: {imported_names!r}"
        )
        return

    assert module_name in _ALLOWED_INTERNAL_API_MODULE_IMPORTS, (
        f"{path} imports facade module {module_name!r}"
    )
