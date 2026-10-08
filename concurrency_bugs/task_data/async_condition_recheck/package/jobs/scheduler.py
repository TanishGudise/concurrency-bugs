"""Jobs scheduled to run later."""

from __future__ import annotations

import asyncio
import heapq
import itertools
import time
from collections.abc import Callable
from typing import Any

from jobs.queue import JobQueue


class DelayedJobs:
    """Holds jobs until they are due, then puts them on the queue."""

    def __init__(self, queue: JobQueue, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._queue = queue
        self._clock = clock
        self._heap: list[tuple[float, int, Any]] = []
        self._order = itertools.count()
        self._cond = asyncio.Condition()
        self._stopped = False

    async def schedule(self, job: Any, delay_s: float) -> None:
        async with self._cond:
            heapq.heappush(self._heap, (self._clock() + max(0.0, delay_s), next(self._order), job))
            self._cond.notify()

    def _next_due_in(self) -> float | None:
        if not self._heap:
            return None
        return max(0.0, self._heap[0][0] - self._clock())

    async def run(self) -> None:
        """Move due jobs to the queue until stopped."""
        while True:
            async with self._cond:
                # Re-check after every wake-up: a new, earlier job may have arrived, or nothing
                # may be due yet.
                while not self._stopped and (self._next_due_in() is None or self._next_due_in() > 0):
                    timeout = self._next_due_in()
                    try:
                        await asyncio.wait_for(self._cond.wait(), timeout)
                    except TimeoutError:
                        pass
                if self._stopped:
                    return
                _, _, job = heapq.heappop(self._heap)
            await self._queue.put(job)

    async def stop(self) -> None:
        async with self._cond:
            self._stopped = True
            self._cond.notify_all()

    def __len__(self) -> int:
        return len(self._heap)
