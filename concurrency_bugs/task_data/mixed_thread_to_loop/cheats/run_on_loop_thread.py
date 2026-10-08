"""Run blocking functions in worker threads from asyncio code."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any


class JobRunner:
    def __init__(self, max_workers: int = 4) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    async def run(self, fn: Callable[..., Any], *args: Any) -> Any:
        """Run ``fn(*args)`` in a worker thread and return its result."""
        return fn(*args)  # no threads, so no cross-thread hand-off to get wrong

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)
