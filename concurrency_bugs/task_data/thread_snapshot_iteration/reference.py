"""Publish/subscribe hub shared by worker threads."""

from __future__ import annotations

import itertools
import threading
from collections.abc import Callable
from typing import Any

Callback = Callable[[Any], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[int, Callback] = {}
        self._tokens = itertools.count()
        self._lock = threading.Lock()

    def subscribe(self, callback: Callback) -> int:
        with self._lock:
            token = next(self._tokens)
            self._subscribers[token] = callback
            return token

    def unsubscribe(self, token: int) -> None:
        with self._lock:
            self._subscribers.pop(token, None)

    def publish(self, event: Any) -> int:
        """Call every subscriber with ``event``; return how many were called."""
        # Take a snapshot under the lock, then call the callbacks *outside* it, so slow or
        # re-entrant callbacks never block (or deadlock) subscribe/unsubscribe.
        with self._lock:
            callbacks = list(self._subscribers.values())
        for callback in callbacks:
            callback(event)
        return len(callbacks)
