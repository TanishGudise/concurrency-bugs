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
        query_task = asyncio.ensure_future(conn.execute(query))
        try:
            result = await asyncio.shield(query_task)
        except asyncio.CancelledError:
            await query_task  # let the query finish so the connection is clean, then reuse it
            self._pool.release(conn)
            raise
        except BaseException:
            self._pool.release(conn)
            raise
        self._pool.release(conn)
        return result
