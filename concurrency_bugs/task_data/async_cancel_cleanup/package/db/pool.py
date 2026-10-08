"""Connection pool."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class Connection(Protocol):
    async def execute(self, query: str, *params: Any) -> list[tuple[Any, ...]]: ...
    def close(self) -> None: ...


class PoolClosed(Exception):
    pass


class Pool:
    """Up to `size` connections, opened on demand and reused.

    - `acquire()` waits for capacity, then returns an idle connection or opens a new one.
    - `release(conn)` returns a healthy connection to the idle set for reuse.
    - `discard(conn)` closes a connection that must not be reused (for example, one in an
      unknown state) and frees its capacity; a fresh connection is opened on a later acquire.
    """

    def __init__(self, connect: Callable[[], Awaitable[Connection]], size: int = 5) -> None:
        if size < 1:
            raise ValueError("size must be at least 1")
        self._connect = connect
        self.size = size
        self._capacity = asyncio.Semaphore(size)
        self._idle: deque[Connection] = deque()
        self._in_use: set[int] = set()
        self._closed = False
        self.opened = 0

    async def acquire(self) -> Connection:
        if self._closed:
            raise PoolClosed()
        await self._capacity.acquire()
        try:
            conn = self._idle.popleft() if self._idle else await self._open()
        except BaseException:
            self._capacity.release()
            raise
        self._in_use.add(id(conn))
        return conn

    async def _open(self) -> Connection:
        conn = await self._connect()
        self.opened += 1
        return conn

    def release(self, conn: Connection) -> None:
        self._in_use.discard(id(conn))
        if self._closed:
            conn.close()
        else:
            self._idle.append(conn)
        self._capacity.release()

    def discard(self, conn: Connection) -> None:
        self._in_use.discard(id(conn))
        try:
            conn.close()
        except Exception:
            logger.exception("closing a discarded connection failed")
        self._capacity.release()

    @property
    def in_use(self) -> int:
        return len(self._in_use)

    @property
    def idle(self) -> int:
        return len(self._idle)

    def close(self) -> None:
        self._closed = True
        while self._idle:
            self._idle.popleft().close()
