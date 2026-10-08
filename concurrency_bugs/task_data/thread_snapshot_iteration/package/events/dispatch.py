"""Run callbacks on a worker pool instead of the publishing thread."""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

_STOP = object()


class ThreadedDispatcher:
    """Wraps callbacks so they run on background workers, in submission order per worker.

    The lock only guards the pending counter and is held for a few instructions, never while
    a callback runs.
    """

    def __init__(self, workers: int = 2) -> None:
        self._queue: queue.Queue[Any] = queue.Queue()
        self._lock = threading.Lock()
        self._pending = 0
        self._idle = threading.Condition(self._lock)
        self._threads = [
            threading.Thread(target=self._work, daemon=True, name=f"dispatch-{i}") for i in range(workers)
        ]
        for thread in self._threads:
            thread.start()

    def wrap(self, callback: Callable[[str, Any], None]) -> Callable[[str, Any], None]:
        def deferred(topic: str, event: Any) -> None:
            with self._lock:
                self._pending += 1
            self._queue.put((callback, topic, event))

        return deferred

    def _work(self) -> None:
        while True:
            item = self._queue.get()
            if item is _STOP:
                return
            callback, topic, event = item
            try:
                callback(topic, event)
            except Exception:
                logger.exception("deferred callback for %s failed", topic)
            finally:
                with self._lock:
                    self._pending -= 1
                    if self._pending == 0:
                        self._idle.notify_all()

    def drain(self) -> None:
        """Block until every deferred callback submitted so far has run."""
        with self._idle:
            while self._pending:
                self._idle.wait()

    def close(self) -> None:
        for _ in self._threads:
            self._queue.put(_STOP)
        for thread in self._threads:
            thread.join()
