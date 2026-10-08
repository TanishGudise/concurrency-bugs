"""Publish/subscribe hub shared by worker threads."""

from __future__ import annotations

import itertools
from collections.abc import Callable
from typing import Any

Callback = Callable[[Any], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[int, Callback] = {}
        self._tokens = itertools.count()

    def subscribe(self, callback: Callback) -> int:
        token = next(self._tokens)
        self._subscribers[token] = callback
        return token

    def unsubscribe(self, token: int) -> None:
        self._subscribers.pop(token, None)

    def publish(self, event: Any) -> int:
        """Call every subscriber with ``event``; return how many were called."""
        called = 0
        for callback in self._subscribers.values():
            callback(event)
            called += 1
        return called
