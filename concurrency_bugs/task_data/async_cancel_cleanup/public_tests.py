import asyncio

from db import ConnectionLost, Database, Pool


class FakeConnection:
    def __init__(self, ident):
        self.ident = ident
        self.closed = False

    async def execute(self, query, *params):
        return [(self.ident, query, params)]

    def close(self):
        self.closed = True


def make_pool(size=2):
    opened = []

    async def connect():
        conn = FakeConnection(len(opened) + 1)
        opened.append(conn)
        return conn

    return Pool(connect, size=size), opened


def test_fetch_returns_rows_and_reuses_connections():
    async def main():
        pool, opened = make_pool()
        db = Database(pool)
        assert await db.fetch("select 1") == [(1, "select 1", ())]
        assert await db.fetch_one("select ?", 2) == (1, "select ?", (2,))
        return pool, opened

    pool, opened = asyncio.run(main())
    assert len(opened) == 1 and pool.idle == 1 and pool.in_use == 0


def test_discarded_connections_are_replaced():
    async def main():
        pool, opened = make_pool(size=1)
        conn = await pool.acquire()
        pool.discard(conn)
        fresh = await pool.acquire()
        return conn, fresh

    conn, fresh = asyncio.run(main())
    assert conn.closed and fresh is not conn


def test_idempotent_reads_retry_lost_connections():
    attempts = []

    async def main():
        pool, _ = make_pool()
        db = Database(pool)
        real_fetch = db.fetch

        async def flaky(query, *params):
            attempts.append(query)
            if len(attempts) == 1:
                raise ConnectionLost()
            return await real_fetch(query, *params)

        db.fetch = flaky
        return await db.fetch_idempotent("select 1")

    assert asyncio.run(main())[0][1] == "select 1" and len(attempts) == 2
