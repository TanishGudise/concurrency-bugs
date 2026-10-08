"""In-memory registry of user records, created in the database on first sight."""

from __future__ import annotations

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

    def __len__(self) -> int:
        return len(self._users)

    def cached(self, name: str) -> Any | None:
        return self._users.get(normalize_name(name))

    async def get_or_create(self, name: str) -> Any:
        """Return the user with this username, creating it on first use."""
        name = normalize_name(name)
        if name in self._users:
            return self._users[name]
        user = await self._db.create_user(name)
        self._users[name] = user
        logger.info("created user %s", name)
        return user

    async def get_by_email(self, email: str) -> Any:
        """Return the user for an email address, creating it on first use."""
        name = normalize_name(await self._directory.name_for(email))
        if name in self._users:
            return self._users[name]
        user = await self._db.create_user(name, email=email)
        self._users[name] = user
        logger.info("created user %s from email sign-in", name)
        return user
