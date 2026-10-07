import asyncio

from registry import UserRegistry


class FakeDatabase:
    def __init__(self):
        self.created = []

    async def create_user(self, name):
        self.created.append(name)
        return {"name": name, "row": len(self.created)}


def test_user_is_created_once_and_cached():
    async def main():
        db = FakeDatabase()
        registry = UserRegistry(db)
        first = await registry.get_or_create("ada")
        second = await registry.get_or_create("ada")
        return db, first, second

    db, first, second = asyncio.run(main())
    assert first is second
    assert first["name"] == "ada"
    assert db.created == ["ada"]


def test_different_names_get_different_users():
    async def main():
        db = FakeDatabase()
        registry = UserRegistry(db)
        return db, await registry.get_or_create("ada"), await registry.get_or_create("bob")

    db, ada, bob = asyncio.run(main())
    assert ada is not bob
    assert db.created == ["ada", "bob"]
