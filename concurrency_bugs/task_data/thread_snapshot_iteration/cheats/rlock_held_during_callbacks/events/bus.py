"""The event bus shared by all component threads."""

from __future__ import annotations

import itertools
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from events.topics import compile_pattern, matches

logger = logging.getLogger(__name__)

Callback = Callable[[str, Any], None]


@dataclass(frozen=True)
class Subscription:
    pattern: str
    callback: Callback


class EventBus:
    def __init__(self, *, on_error: Callable[[Exception], None] | None = None) -> None:
        self._subscriptions: dict[int, Subscription] = {}
        self._tokens = itertools.count(1)
        self._on_error = on_error
        self.published = 0
        self._lock = threading.RLock()  # re-entrant, so callbacks can unsubscribe

    def subscribe(self, pattern: str, callback: Callback) -> int:
        compile_pattern(pattern)  # validate early
        with self._lock:
            token = next(self._tokens)
            self._subscriptions[token] = Subscription(pattern, callback)
            return token

    def unsubscribe(self, token: int) -> None:
        with self._lock:
            self._subscriptions.pop(token, None)

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscriptions)

    def publish(self, topic: str, event: Any) -> int:
        """Call every matching subscriber with (topic, event); return how many were called."""
        with self._lock:
            self.published += 1
            called = 0
            for subscription in self._subscriptions.values():
                if not matches(subscription.pattern, topic):
                    continue
                called += 1
                try:
                    subscription.callback(topic, event)
                except Exception as exc:
                    if self._on_error is None:
                        raise
                    self._on_error(exc)
            return called
