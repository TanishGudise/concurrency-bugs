"""Per-host request rate limiting (a politeness rule separate from concurrency)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from urllib.parse import urlsplit


class TokenBucket:
    """Allows `rate` requests per second on average, with bursts of up to `burst`."""

    def __init__(self, rate: float, burst: int, clock: Callable[[], float] = time.monotonic) -> None:
        if rate <= 0 or burst < 1:
            raise ValueError("rate must be positive and burst at least 1")
        self.rate = rate
        self.burst = burst
        self._clock = clock
        self._tokens = float(burst)
        self._updated = clock()

    def _refill(self) -> None:
        now = self._clock()
        self._tokens = min(self.burst, self._tokens + (now - self._updated) * self.rate)
        self._updated = now

    def time_until_available(self) -> float:
        self._refill()
        if self._tokens >= 1:
            return 0.0
        return (1 - self._tokens) / self.rate

    def take(self) -> None:
        self._refill()
        self._tokens -= 1


class HostRateLimiter:
    """One token bucket per host. Runs on the event loop thread only, so no locking."""

    def __init__(self, rate: float = 2.0, burst: int = 4) -> None:
        self._rate = rate
        self._burst = burst
        self._buckets: dict[str, TokenBucket] = {}

    def bucket(self, url: str) -> TokenBucket:
        host = urlsplit(url).hostname or ""
        if host not in self._buckets:
            self._buckets[host] = TokenBucket(self._rate, self._burst)
        return self._buckets[host]

    async def acquire(self, url: str) -> None:
        bucket = self.bucket(url)
        while (wait := bucket.time_until_available()) > 0:
            await asyncio.sleep(wait)
        bucket.take()
