"""Where uploaded bytes go."""

from __future__ import annotations

import asyncio
from typing import Protocol


class SinkClosed(Exception):
    pass


class Sink(Protocol):
    async def write(self, offset: int, data: bytes) -> None: ...
    async def close(self) -> None: ...


class BufferSink:
    """Assembles parts in memory. Writes may arrive in any order; offsets place them.

    Single event loop only. The lock keeps a write and close() from interleaving across the
    await in `_flush_if_due`.
    """

    def __init__(self, *, flush_every: int = 1 << 20) -> None:
        self._chunks: dict[int, bytes] = {}
        self._closed = False
        self._lock = asyncio.Lock()
        self._unflushed = 0
        self._flush_every = flush_every
        self.flushes = 0

    async def write(self, offset: int, data: bytes) -> None:
        async with self._lock:
            if self._closed:
                raise SinkClosed("write to closed sink")
            self._chunks[offset] = bytes(data)
            self._unflushed += len(data)
            await self._flush_if_due()

    async def _flush_if_due(self) -> None:
        if self._unflushed >= self._flush_every:
            await asyncio.sleep(0)  # a real sink would hand data to the OS here
            self._unflushed = 0
            self.flushes += 1

    async def close(self) -> None:
        async with self._lock:
            self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed

    def getvalue(self) -> bytes:
        return b"".join(self._chunks[offset] for offset in sorted(self._chunks))
