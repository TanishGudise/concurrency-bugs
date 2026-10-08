"""Database and directory interfaces, plus a retrying database wrapper."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class TransientDatabaseError(Exception):
    """A failure worth retrying (connection reset, failover in progress)."""


class Database(Protocol):
    async def create_user(self, name: str, email: str | None = None) -> Any: ...
    async def load_profile(self, user_id: Any) -> dict[str, Any]: ...


class Directory(Protocol):
    async def name_for(self, email: str) -> str: ...


class RetryingDatabase:
    """Wraps a `Database` and retries transient errors with a short backoff.

    Non-transient errors (constraint violations, bad input) are raised immediately.
    """

    def __init__(self, inner: Database, *, attempts: int = 3, backoff_s: float = 0.05) -> None:
        if attempts < 1:
            raise ValueError("attempts must be at least 1")
        self._inner = inner
        self._attempts = attempts
        self._backoff_s = backoff_s

    async def _retry(self, operation: str, call: Any) -> Any:
        for attempt in range(1, self._attempts + 1):
            try:
                return await call()
            except TransientDatabaseError:
                if attempt == self._attempts:
                    raise
                logger.warning("%s failed (attempt %d), retrying", operation, attempt)
                await asyncio.sleep(self._backoff_s * attempt)
        raise AssertionError("unreachable")

    async def create_user(self, name: str, email: str | None = None) -> Any:
        return await self._retry("create_user", lambda: self._inner.create_user(name, email))

    async def load_profile(self, user_id: Any) -> dict[str, Any]:
        return await self._retry("load_profile", lambda: self._inner.load_profile(user_id))
