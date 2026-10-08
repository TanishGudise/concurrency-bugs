"""Query helper over a small connection pool."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol


class Connection(Protocol):
    async def execute(self, query: str) -> Any: ...


class Pool(Protocol):
    async def acquire(self) -> Connection: ...
    def release(self, conn: Connection) -> None: ...
    def discard(self, conn: Connection) -> None: ...


class Database:
    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def fetch(self, query: str) -> Any:
        """Run ``query`` on a pooled connection and return its result."""
        conn = await self._pool.acquire()
        try:
            result = await conn.execute(query)
        except asyncio.CancelledError:
            # Interrupted mid-query: the connection may still have a half-finished query on
            # it, so it must not be reused. Discard it and let the cancellation propagate.
            self._pool.discard(conn)
            raise
        except BaseException:
            self._pool.release(conn)
            raise
        self._pool.release(conn)
        return result
