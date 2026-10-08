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
        self._creating: dict[str, asyncio.Future[Any]] = {}

    async def get_or_create(self, name: str) -> Any:
        """Return the user called ``name``, creating it on first use."""
        if name in self._users:
            return self._users[name]
        creation = self._creating.get(name)
        if creation is None:
            creation = asyncio.ensure_future(self._db.create_user(name))
            self._creating[name] = creation
        user = await creation
        self._users[name] = user
        self._creating.pop(name, None)
        return user
