"""Run blocking functions in worker threads from asyncio code."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any


class JobRunner:
    def __init__(self, max_workers: int = 4) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    async def run(self, fn: Callable[..., Any], *args: Any) -> Any:
        """Run ``fn(*args)`` in a worker thread and return its result."""
        loop = asyncio.get_running_loop()
        result = loop.create_future()

        def on_done(job: Future[Any]) -> None:
            error = job.exception()
            if error is not None:
                loop.call_soon_threadsafe(result.set_exception, error)
            else:
                loop.call_soon_threadsafe(result.set_result, job.result())

        self._executor.submit(fn, *args).add_done_callback(on_done)
        return await result

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)
