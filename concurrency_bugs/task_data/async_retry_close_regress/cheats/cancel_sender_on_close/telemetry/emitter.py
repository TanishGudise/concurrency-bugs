"""Background emitter for one job counter."""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol

from telemetry.backoff import Backoff

logger = logging.getLogger(__name__)


class SendError(Exception):
    """The collector could not be reached or rejected the request temporarily."""


class Transport(Protocol):
    async def send(self, value: int) -> None: ...


class MetricEmitter:
    """Use as ``async with MetricEmitter(transport) as emitter: emitter.report(n)``."""

    def __init__(
        self, transport: Transport, backoff: Backoff | None = None, *, name: str = "counter"
    ) -> None:
        self._transport = transport
        self._backoff = backoff or Backoff()
        self._name = name
        self._pending: int | None = None  # newest value not yet delivered
        self._closed = False
        self._wakeup = asyncio.Event()
        self._sender: asyncio.Task[None] | None = None
        self.delivered = 0
        self.failures = 0

    async def __aenter__(self) -> MetricEmitter:
        self._sender = asyncio.create_task(self._run(), name=f"metric-sender:{self._name}")
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    def report(self, value: int) -> None:
        """Record the counter's new value. Never blocks."""
        if self._closed:
            raise RuntimeError("emitter is closed")
        self._pending = value
        self._wakeup.set()

    async def close(self) -> None:
        """Deliver the newest value, then stop the sender."""
        if self._closed:
            return
        self._closed = True
        self._wakeup.set()
        if self._sender is not None:
            self._sender.cancel()
            try:
                await self._sender
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        while True:
            await self._wakeup.wait()
            self._wakeup.clear()
            attempt = 0
            while self._pending is not None:
                value = self._pending
                self._pending = None
                try:
                    await self._transport.send(value)
                    self.delivered += 1
                    attempt = 0
                except SendError as exc:
                    self.failures += 1
                    attempt += 1
                    logger.warning("%s: send of %d failed (%s); retry %d", self._name, value, exc, attempt)
                    await self._backoff.wait(attempt)
                    # Retry the failed value only if nothing newer was reported during the wait;
                    # otherwise the newer value replaces it (putting the old one back would
                    # overwrite, and lose, the newer value).
                    if self._pending is None:
                        self._pending = value
            if self._closed:
                return
