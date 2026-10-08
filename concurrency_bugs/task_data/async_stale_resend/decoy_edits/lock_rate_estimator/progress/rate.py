"""Throughput and ETA estimates from reported progress values."""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable


class RateEstimator:
    """Keeps a sliding window of (time, progress) samples.

    Everything runs on the event loop thread, so the window is shared without locking.
    """

    def __init__(
        self, total: float, *, window: int = 20, clock: Callable[[], float] = time.monotonic
    ) -> None:
        if total <= 0:
            raise ValueError("total must be positive")
        self._total = total
        self._clock = clock
        self._samples: deque[tuple[float, float]] = deque(maxlen=window)
        self._lock = threading.Lock()

    def observe(self, progress: float) -> None:
        with self._lock:
            self._samples.append((self._clock(), progress))

    @property
    def rate(self) -> float | None:
        """Progress units per second over the window, or None with fewer than two samples."""
        if len(self._samples) < 2:
            return None
        (t0, p0), (t1, p1) = self._samples[0], self._samples[-1]
        if t1 <= t0:
            return None
        return (p1 - p0) / (t1 - t0)

    @property
    def eta_seconds(self) -> float | None:
        rate = self.rate
        if not rate or rate <= 0 or not self._samples:
            return None
        remaining = self._total - self._samples[-1][1]
        return max(0.0, remaining / rate)

    def fraction(self) -> float:
        if not self._samples:
            return 0.0
        return min(1.0, self._samples[-1][1] / self._total)
