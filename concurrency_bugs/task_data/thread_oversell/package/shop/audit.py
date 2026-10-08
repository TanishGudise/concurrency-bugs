"""Audit trail of reservation attempts."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Protocol

logger = logging.getLogger(__name__)

Record = tuple[float, str, int, bool]


class AuditLog(Protocol):
    def record(self, item: str, quantity: int, ok: bool) -> None: ...


class AuditClient:
    """Buffers audit records and ships them to the audit service in batches.

    `record()` only appends to an in-memory buffer; a background thread wakes up every
    `interval_s` (or when the buffer is full) and sends the batch with `ship(batch)`, which is
    a slow network call. The buffer lock is held only to swap the buffer, never while shipping.
    """

    def __init__(
        self, ship: Callable[[list[Record]], None], *, interval_s: float = 1.0, max_batch: int = 500
    ) -> None:
        self._ship = ship
        self._interval_s = interval_s
        self._max_batch = max_batch
        self._buffer: list[Record] = []
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stopping = False
        self._thread = threading.Thread(target=self._run, name="audit-shipper", daemon=True)
        self.shipped = 0

    def start(self) -> None:
        self._thread.start()

    def record(self, item: str, quantity: int, ok: bool) -> None:
        with self._lock:
            self._buffer.append((time.time(), item, quantity, ok))
            full = len(self._buffer) >= self._max_batch
        if full:
            self._wake.set()

    def _take(self) -> list[Record]:
        with self._lock:
            batch, self._buffer = self._buffer, []
        return batch

    def _run(self) -> None:
        while not self._stopping:
            self._wake.wait(self._interval_s)
            self._wake.clear()
            batch = self._take()
            if batch:
                try:
                    self._ship(batch)
                    self.shipped += len(batch)
                except Exception:
                    logger.exception("shipping %d audit records failed; re-queueing", len(batch))
                    with self._lock:
                        self._buffer[:0] = batch

    def close(self) -> None:
        self._stopping = True
        self._wake.set()
        if self._thread.is_alive():
            self._thread.join()
        batch = self._take()
        if batch:
            self._ship(batch)
            self.shipped += len(batch)
