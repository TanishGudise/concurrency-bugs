"""Retrying transient fetch failures."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class TransientFetchError(Exception):
    """Timeouts, connection resets and 5xx responses: worth retrying."""


class Backoff:
    """Exponential backoff with jitter: base * 2**attempt, capped, +/- jitter."""

    def __init__(self, base_s: float = 0.2, cap_s: float = 10.0, jitter: float = 0.1) -> None:
        self.base_s = base_s
        self.cap_s = cap_s
        self.jitter = jitter

    def delay(self, attempt: int) -> float:
        raw = min(self.cap_s, self.base_s * (2**attempt))
        return max(0.0, raw * (1 + random.uniform(-self.jitter, self.jitter)))

    async def wait(self, attempt: int) -> None:
        await asyncio.sleep(self.delay(attempt))


async def with_retries(call: Callable[[], Awaitable[T]], *, attempts: int, backoff: Backoff) -> T:
    """Call ``call()`` up to ``attempts`` times, waiting between transient failures."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    for attempt in range(attempts):
        try:
            return await call()
        except TransientFetchError:
            if attempt == attempts - 1:
                raise
            await backoff.wait(attempt)
    raise AssertionError("unreachable")
