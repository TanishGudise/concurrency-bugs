"""Progress reports from worker threads back to async code."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


class ProgressReporter:
    """Lets a job running on a worker thread report progress to an async callback.

    `report()` is called on the worker thread. It hands the callback to the event loop with
    `run_coroutine_threadsafe`, which is safe from any thread, and waits for it to finish so
    reports arrive in order.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, callback: Callable[[float], Awaitable[None]]) -> None:
        self._loop = loop
        self._callback = callback
        self.reports = 0

    def report(self, fraction: float, *, timeout_s: float = 10.0) -> None:
        if not 0.0 <= fraction <= 1.0:
            raise ValueError("progress must be between 0 and 1")
        future = asyncio.run_coroutine_threadsafe(self._callback(fraction), self._loop)
        future.result(timeout=timeout_s)
        self.reports += 1
