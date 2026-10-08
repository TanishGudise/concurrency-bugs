"""User registry with lazy, de-duplicated creation."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol


class Database(Protocol):
    async def create_user(self, name: str) -> Any: ...


class UserRegistry:
    """Caches users by name; concurrent callers for a new name share one database call."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._users: dict[str, Any] = {}
        self._creating: dict[str, asyncio.Task[Any]] = {}

    async def get_or_create(self, name: str) -> Any:
        """Return the user called ``name``, creating it on first use."""
        if name in self._users:
            return self._users[name]
        creation = self._creating.get(name)
        if creation is None:
            creation = asyncio.ensure_future(self._create(name))
            self._creating[name] = creation
        # shield: cancelling this caller cancels only its wait, not the shared creation.
        return await asyncio.shield(creation)

    async def _create(self, name: str) -> Any:
        try:
            user = await self._db.create_user(name)
            self._users[name] = user
            return user
        finally:
            # Runs on success *and* failure, so a failed creation is never reused.
            del self._creating[name]
