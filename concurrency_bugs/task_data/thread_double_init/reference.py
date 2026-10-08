"""Lazily created shared client."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class LazyClient(Generic[T]):
    """Creates the client on first use with ``factory`` (slow: it opens network connections)."""

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._client: T | None = None
        self._lock = threading.Lock()

    def get(self) -> T:
        client = self._client
        if client is not None:  # fast path once created: no locking
            return client
        with self._lock:
            # Check again under the lock: another thread may have created it while we waited.
            if self._client is None:
                self._client = self._factory()
            return self._client
