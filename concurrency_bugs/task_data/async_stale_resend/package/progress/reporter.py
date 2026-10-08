"""Coalescing progress reporter.

The job calls ``report()`` as often as it likes; a single background sender delivers values
to the transport one at a time, always sending the newest value it has. On ``close()`` the
reporter flushes, and repeats the final value so the dashboard can mark the job finished.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


class Transport(Protocol):
    async def send(self, value: float) -> None: ...


@dataclass
class ReporterStats:
    reported: int = 0
    delivered: int = 0
    coalesced: int = 0


class ProgressReporter:
    """Use as ``async with ProgressReporter(transport) as reporter: ...``."""

    def __init__(self, transport: Transport, *, name: str = "job") -> None:
        self._transport = transport
        self._name = name
        self._pending: float | None = None  # newest value the sender has not picked up yet
        self._last_sent: float | None = None  # last value the transport accepted
        self._closed = False
        self._wakeup = asyncio.Event()
        self._sender: asyncio.Task[None] | None = None
        self.stats = ReporterStats()

    async def __aenter__(self) -> ProgressReporter:
        self.start()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    def start(self) -> None:
        if self._sender is None:
            self._sender = asyncio.create_task(self._run(), name=f"progress-sender:{self._name}")

    @property
    def latest(self) -> float | None:
        """The newest value reported so far."""
        if self._pending is not None:
            return self._pending
        return self._last_sent

    @property
    def closed(self) -> bool:
        return self._closed

    def report(self, value: float) -> None:
        """Record a new progress value. Never blocks; progress must not decrease."""
        if self._closed:
            raise RuntimeError("reporter is closed")
        latest = self.latest
        if latest is not None and value < latest:
            raise ValueError(f"progress went backwards: {value} < {latest}")
        if self._pending is not None:
            self.stats.coalesced += 1
        self._pending = value
        self.stats.reported += 1
        self._wakeup.set()

    async def close(self) -> None:
        """Deliver pending progress, repeat the final value, and stop the sender."""
        if self._closed:
            return
        self._closed = True
        if self._pending is None and self._last_sent is not None:
            # Repeat the final value: the dashboard treats it as the end-of-job marker.
            self._pending = self._last_sent
        self._wakeup.set()
        if self._sender is not None:
            await self._sender
        logger.debug("reporter %s closed after %d deliveries", self._name, self.stats.delivered)

    async def _run(self) -> None:
        while True:
            await self._wakeup.wait()
            self._wakeup.clear()
            while self._pending is not None:
                value = self._pending
                self._pending = None
                await self._transport.send(value)
                self._last_sent = value
                self.stats.delivered += 1
            if self._closed:
                return
