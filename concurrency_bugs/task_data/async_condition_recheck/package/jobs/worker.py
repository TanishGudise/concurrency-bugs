"""A pool of worker coroutines consuming a JobQueue."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from jobs.queue import JobQueue

logger = logging.getLogger(__name__)

Handler = Callable[[Any], Awaitable[None]]


class WorkerPool:
    """Runs `size` workers. A failing job is logged and does not stop its worker."""

    def __init__(self, queue: JobQueue, handler: Handler, *, size: int = 4) -> None:
        if size < 1:
            raise ValueError("size must be at least 1")
        self._queue = queue
        self._handler = handler
        self._size = size
        self._tasks: list[asyncio.Task[None]] = []
        self.completed = 0
        self.failed = 0

    async def _worker(self, index: int) -> None:
        while True:
            job = await self._queue.get()
            try:
                await self._handler(job)
                self.completed += 1
            except Exception:
                self.failed += 1
                logger.exception("worker %d: job %r failed", index, job)

    def start(self) -> None:
        if self._tasks:
            raise RuntimeError("pool already started")
        self._tasks = [
            asyncio.create_task(self._worker(i), name=f"job-worker-{i}") for i in range(self._size)
        ]

    async def stop(self) -> None:
        """Stop the workers. Jobs still in the queue stay there."""
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []

    @property
    def running(self) -> int:
        return sum(1 for task in self._tasks if not task.done())
