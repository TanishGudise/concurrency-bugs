"""Backoff between retries of a failed send."""

from __future__ import annotations

import asyncio
import random


class Backoff:
    """Exponential backoff with full jitter: a random wait in [0, min(cap, base * 2**attempt)]."""

    def __init__(
        self, base_s: float = 0.25, cap_s: float = 10.0, *, rng: random.Random | None = None
    ) -> None:
        if base_s < 0 or cap_s < 0:
            raise ValueError("backoff times must not be negative")
        self.base_s = base_s
        self.cap_s = cap_s
        self._rng = rng or random.Random()
        self.waits = 0

    def delay(self, attempt: int) -> float:
        ceiling = min(self.cap_s, self.base_s * (2 ** max(0, attempt - 1)))
        return self._rng.uniform(0, ceiling)

    async def wait(self, attempt: int) -> None:
        """Wait before retry number ``attempt`` (1 for the first retry)."""
        self.waits += 1
        await asyncio.sleep(self.delay(attempt))
