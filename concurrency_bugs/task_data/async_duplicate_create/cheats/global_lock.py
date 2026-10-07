"""User registry with lazy creation."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol


class Database(Protocol):
    async def create_user(self, name: str) -> Any: ...


class UserRegistry:
    """Caches users by name and creates each one in the database on first use."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._users: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, name: str) -> Any:
        """Return the user called ``name``, creating it on first use."""
        async with self._lock:
            if name in self._users:
                return self._users[name]
            user = await self._db.create_user(name)
            self._users[name] = user
            return user
