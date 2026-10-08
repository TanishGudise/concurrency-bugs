"""In-memory registry of user records, created in the database on first sight."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from accounts.db import Database, Directory

logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    name = name.strip().lower()
    if not name or any(ch.isspace() for ch in name):
        raise ValueError(f"invalid username: {name!r}")
    return name


class UserRegistry:
    """Caches users by username. Users are created in the database on first use."""

    def __init__(self, db: Database, directory: Directory) -> None:
        self._db = db
        self._directory = directory
        self._users: dict[str, Any] = {}
        # One in-progress creation per username, shared by both entry points. It is
        # registered before the first await, so concurrent callers find it.
        self._creating: dict[str, asyncio.Task[Any]] = {}

    def __len__(self) -> int:
        return len(self._users)

    def cached(self, name: str) -> Any | None:
        return self._users.get(normalize_name(name))

    async def get_or_create(self, name: str) -> Any:
        """Return the user with this username, creating it on first use."""
        return await self._get(normalize_name(name), email=None)

    async def get_by_email(self, email: str) -> Any:
        """Return the user for an email address, creating it on first use."""
        name = normalize_name(await self._directory.name_for(email))
        if name in self._users:
            return self._users[name]
        user = await self._db.create_user(name, email=email)
        self._users[name] = user
        return user

    async def _get(self, name: str, email: str | None) -> Any:
        if name in self._users:
            return self._users[name]
        creation = self._creating.get(name)
        if creation is None:
            creation = asyncio.ensure_future(self._create(name, email))
            self._creating[name] = creation
        return await asyncio.shield(creation)

    async def _create(self, name: str, email: str | None) -> Any:
        try:
            user = await self._db.create_user(name, email=email)
            self._users[name] = user
            logger.info("created user %s", name)
            return user
        finally:
            del self._creating[name]
