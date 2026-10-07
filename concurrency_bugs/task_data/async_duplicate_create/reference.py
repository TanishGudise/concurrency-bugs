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
        # One in-progress creation per name. It is registered before the first await,
        # so a second caller sees it instead of passing the "not cached" check too.
        self._creating: dict[str, asyncio.Task[Any]] = {}

    async def get_or_create(self, name: str) -> Any:
        """Return the user called ``name``, creating it on first use."""
        if name in self._users:
            return self._users[name]
        creation = self._creating.get(name)
        if creation is None:
            creation = asyncio.ensure_future(self._create(name))
            self._creating[name] = creation
        # shield: one caller being cancelled must not cancel the creation others wait on.
        return await asyncio.shield(creation)

    async def _create(self, name: str) -> Any:
        try:
            user = await self._db.create_user(name)
            self._users[name] = user
            return user
        finally:
            del self._creating[name]
