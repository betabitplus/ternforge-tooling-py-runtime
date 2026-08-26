# %%
"""Py-lib-runtime public config boundary scenario.

Why:
    Verifies that the top-level package API can install and read a runtime
    config snapshot end to end.

Covers:
    Area: public package boundary
    Behavior: runtime config install/read lifecycle
    Interface: top-level `py_lib_runtime`

Checks:
    If a caller installs a runtime config from the supported package boundary,
    then subsequent public reads return the installed immutable snapshot.

Examples:
    Run manually:
        uv run python -m \
            tests.py_lib_runtime.e2e.public_boundary.test_public_config_pipeline

    Run as test:
        pytest tests/py_lib_runtime/e2e/public_boundary/test_public_config_pipeline.py
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from py_lib_runtime import PyLibRuntimeConfig, get_config, install_config

pytestmark = [pytest.mark.hermetic]


@pytest.fixture(autouse=True)
def restore_runtime_config() -> Iterator[None]:
    """Restore installed runtime config after each scenario."""
    original_config = get_config()
    yield
    install_config(original_config)


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> PyLibRuntimeConfig:
    """Run the public runtime config install/read flow."""
    config = PyLibRuntimeConfig(cache_env_var="PIPELINE_CACHE_DIR")
    install_config(config)
    return get_config()


# =============================================================================
# Assertions
# =============================================================================


def assert_public_config_response(config: PyLibRuntimeConfig) -> None:
    """Assert the public config snapshot reflects the installed value."""
    assert config.cache_env_var == "PIPELINE_CACHE_DIR"


# =============================================================================
# Tests
# =============================================================================


def test_public_config_pipeline() -> None:
    """The public config lifecycle works through the top-level package."""
    config = run_pipeline()

    assert_public_config_response(config)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the public config boundary scenario as a manual demo."""
    config = run_pipeline()
    assert_public_config_response(config)


if __name__ == "__main__":
    main()

# %%
