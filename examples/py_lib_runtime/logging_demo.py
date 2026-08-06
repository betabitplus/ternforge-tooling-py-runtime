# %%
"""Runnable structured logging helper examples.

Run from the repository root:
    uv run python packages/py-lib-runtime/examples/py_lib_runtime/logging_demo.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import cast

from py_lib_runtime import (
    RetryState,
    build_retry_before_sleep_logger,
    configure_package_logging,
    get_logger,
    log_operation_duration,
    log_retry_exhausted,
)


@dataclass(frozen=True)
class DemoNextAction:
    """Small tenacity-like next-action object for the retry callback."""

    sleep: float


@dataclass(frozen=True)
class DemoStop:
    """Small tenacity-like stop metadata object."""

    max_attempt_number: int = 3


@dataclass(frozen=True)
class DemoRetryObject:
    """Small tenacity-like retry object for the retry callback."""

    stop: DemoStop = field(default_factory=DemoStop)


@dataclass(frozen=True)
class DemoOutcome:
    """Small tenacity-like outcome object for the retry callback."""

    error: BaseException | None

    def exception(self) -> BaseException | None:
        """Return the stored exception."""
        return self.error


@dataclass(frozen=True)
class DemoRetryState:
    """Small tenacity-like retry state for the retry callback."""

    attempt_number: int
    next_action: DemoNextAction | None
    outcome: DemoOutcome | None
    retry_object: DemoRetryObject = field(default_factory=DemoRetryObject)


def main() -> None:
    """Configure logging and emit representative structured events."""
    settings = configure_package_logging("demo_lib", level="INFO", json=False)
    logger = get_logger("demo_lib.worker")

    logger.info(
        "Loaded item",
        event_type="demo_lib.item.loaded",
        item_id="item-123",
    )

    preview = "pending"
    with log_operation_duration(
        logger,
        event_type="demo_lib.operation.completed",
        message="Operation completed",
        level=logging.INFO,
        operation="preview",
    ):
        preview = "ready"

    before_sleep = build_retry_before_sleep_logger(
        logger,
        settings=settings,
        context_getter=lambda: {"job_id": "job-123"},
    )
    before_sleep(
        cast(
            "RetryState",
            DemoRetryState(
                attempt_number=2,
                next_action=DemoNextAction(sleep=1.5),
                outcome=DemoOutcome(RuntimeError("  wait\nlater  ")),
            ),
        )
    )

    log_retry_exhausted(
        logger,
        error=RuntimeError("  service\nunavailable  "),
        settings=settings,
        context={"job_id": "job-123"},
    )
    print(f"preview_status: {preview}")


if __name__ == "__main__":
    main()
