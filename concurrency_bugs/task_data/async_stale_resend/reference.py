"""Coalescing progress reporter."""

from __future__ import annotations

import asyncio
from typing import Protocol


class Transport(Protocol):
    async def send(self, value: float) -> None: ...


class ProgressReporter:
    """Use as ``async with ProgressReporter(transport) as reporter: ...``."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport
        self._pending: float | None = None  # newest value the sender has not picked up yet
        self._in_flight: float | None = None  # value taken by the sender, not yet accepted
        self._last_sent: float | None = None  # last value the transport accepted
        self._closed = False
        self._wakeup = asyncio.Event()
        self._sender: asyncio.Task[None] | None = None

    async def __aenter__(self) -> ProgressReporter:
        self._sender = asyncio.create_task(self._run())
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    @property
    def latest(self) -> float | None:
        """The newest value reported so far: pending, then in flight, then delivered."""
        for value in (self._pending, self._in_flight, self._last_sent):
            if value is not None:
                return value
        return None

    def report(self, value: float) -> None:
        """Record a new progress value. Never blocks; progress must not decrease."""
        if self._closed:
            raise RuntimeError("reporter is closed")
        latest = self.latest
        if latest is not None and value < latest:
            raise ValueError(f"progress went backwards: {value} < {latest}")
        self._pending = value
        self._wakeup.set()

    async def close(self) -> None:
        """Deliver pending progress, re-send the final value, and stop the sender."""
        if self._closed:
            return
        self._closed = True
        # A value in flight is newer than _last_sent and will be delivered, so re-queueing
        # _last_sent then would send an older value after a newer one.
        if self._pending is None and self._in_flight is None and self._last_sent is not None:
            # At-least-once: make sure the receiver sees the final value.
            self._pending = self._last_sent
        self._wakeup.set()
        if self._sender is not None:
            await self._sender

    async def _run(self) -> None:
        while True:
            await self._wakeup.wait()
            self._wakeup.clear()
            while self._pending is not None:
                value = self._pending
                self._pending = None
                self._in_flight = value
                await self._transport.send(value)
                self._last_sent = value
                self._in_flight = None
            if self._closed:
                return
