import asyncio

import pytest
from accounts import ProfileCache, SignInService, UserRegistry


class FakeDatabase:
    def __init__(self):
        self.created = []

    async def create_user(self, name, email=None):
        self.created.append(name)
        return {"id": len(self.created), "name": name, "email": email}

    async def load_profile(self, user_id):
        return {"user_id": user_id, "theme": "dark"}


class FakeDirectory:
    async def name_for(self, email):
        return email.split("@")[0]


def make_service():
    db = FakeDatabase()
    registry = UserRegistry(db, FakeDirectory())
    return db, registry, SignInService(registry, ProfileCache(db))


def test_sign_in_by_name_then_email_reuses_the_user():
    async def main():
        db, registry, service = make_service()
        first = await service.sign_in("Ada")
        second = await service.sign_in("ada@example.com")
        assert first.user is second.user
        assert first.profile["theme"] == "dark"
        return db.created

    assert asyncio.run(main()) == ["ada"]


def test_different_users_are_different():
    async def main():
        db, registry, _ = make_service()
        ada = await registry.get_or_create("ada")
        bob = await registry.get_or_create("bob")
        assert ada is not bob and len(registry) == 2

    asyncio.run(main())


def test_invalid_usernames_are_rejected():
    async def main():
        _, registry, _ = make_service()
        with pytest.raises(ValueError):
            await registry.get_or_create("  ")

    asyncio.run(main())
