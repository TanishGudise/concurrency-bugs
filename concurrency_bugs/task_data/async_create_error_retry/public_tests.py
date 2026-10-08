import asyncio

import pytest
from members import MemberRegistry, TransientError, retry_transient, validate_handle


class FakeDatabase:
    def __init__(self):
        self.created = []

    async def create_member(self, handle):
        self.created.append(handle)
        return {"id": len(self.created), "handle": handle}

    async def count_members(self):
        return len(self.created)


def test_member_is_created_once_and_cached():
    async def main():
        db = FakeDatabase()
        registry = MemberRegistry(db)
        first = await registry.get_or_create("@Ada_L")
        assert await registry.get_or_create("ada_l") is first
        assert "ada_l" in registry
        return db.created

    assert asyncio.run(main()) == ["ada_l"]


def test_concurrent_callers_share_one_creation():
    async def main():
        db = FakeDatabase()
        registry = MemberRegistry(db)
        members = await asyncio.gather(*(registry.get_or_create("ada_l") for _ in range(3)))
        assert all(m is members[0] for m in members)
        return db.created

    assert asyncio.run(main()) == ["ada_l"]


def test_transient_errors_are_retried_by_the_decorator():
    attempts = []

    @retry_transient(3)
    async def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise TransientError()
        return "ok"

    assert asyncio.run(flaky()) == "ok" and len(attempts) == 3


def test_invalid_handles_are_rejected():
    with pytest.raises(ValueError):
        validate_handle("a b")
