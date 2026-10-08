import asyncio

from db import Database


class FakeConnection:
    async def execute(self, query):
        return [query.upper()]


class FakePool:
    def __init__(self):
        self.free = [FakeConnection()]
        self.released = 0

    async def acquire(self):
        return self.free.pop()

    def release(self, conn):
        self.released += 1
        self.free.append(conn)

    def discard(self, conn):
        self.free.append(FakeConnection())


def test_fetch_returns_the_result_and_releases_the_connection():
    async def main():
        pool = FakePool()
        db = Database(pool)
        assert await db.fetch("select 1") == ["SELECT 1"]
        assert await db.fetch("select 2") == ["SELECT 2"]
        return pool

    pool = asyncio.run(main())
    assert pool.released == 2
    assert len(pool.free) == 1
