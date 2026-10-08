"""Sign-in orchestration and the profile cache."""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from typing import Any

from accounts.db import Database
from accounts.registry import UserRegistry


class ProfileCache:
    """Loads user profiles once and shares in-flight loads between concurrent callers.

    A load that fails is not cached, so the next caller tries again.
    """

    def __init__(self, db: Database) -> None:
        self._db = db
        self._profiles: dict[Any, dict[str, Any]] = {}
        self._loading: dict[Any, asyncio.Task[dict[str, Any]]] = {}

    async def get(self, user_id: Any) -> dict[str, Any]:
        if user_id in self._profiles:
            return self._profiles[user_id]
        load = self._loading.get(user_id)
        if load is None:
            load = asyncio.ensure_future(self._load(user_id))
            self._loading[user_id] = load
        return await asyncio.shield(load)

    async def _load(self, user_id: Any) -> dict[str, Any]:
        try:
            profile = await self._db.load_profile(user_id)
            self._profiles[user_id] = profile
            return profile
        finally:
            del self._loading[user_id]

    def invalidate(self, user_id: Any) -> None:
        self._profiles.pop(user_id, None)


@dataclass
class Session:
    user: Any
    profile: dict[str, Any]
    token: str = field(default_factory=lambda: secrets.token_urlsafe(16))


class SignInService:
    def __init__(self, registry: UserRegistry, profiles: ProfileCache) -> None:
        self._registry = registry
        self._profiles = profiles
        self.sign_ins = 0

    async def sign_in(self, login: str) -> Session:
        """Sign in with a username or an email address."""
        if "@" in login:
            user = await self._registry.get_by_email(login)
        else:
            user = await self._registry.get_or_create(login)
        profile = await self._profiles.get(user["id"])
        self.sign_ins += 1
        return Session(user=user, profile=profile)
