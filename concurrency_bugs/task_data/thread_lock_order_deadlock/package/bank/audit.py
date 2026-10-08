"""Audit trail of transfers."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class AuditEntry:
    src: int
    dst: int
    amount: int
    at: float


class AuditTrail:
    """Append-only list of transfers.

    `record()` is called while the caller still holds account locks, so the trail's own lock
    is always taken *after* account locks, and the trail never takes an account lock itself.
    """

    def __init__(self, *, keep: int = 10_000) -> None:
        self._entries: list[AuditEntry] = []
        self._lock = threading.Lock()
        self._keep = keep

    def record(self, src: int, dst: int, amount: int) -> None:
        with self._lock:
            self._entries.append(AuditEntry(src, dst, amount, time.time()))
            if len(self._entries) > self._keep:
                del self._entries[: len(self._entries) - self._keep]

    def entries(self) -> list[AuditEntry]:
        with self._lock:
            return list(self._entries)

    def volume(self, account_id: int) -> int:
        """Total money moved in or out of an account, from the trail."""
        return sum(e.amount for e in self.entries() if account_id in (e.src, e.dst))
