import asyncio

import pytest
from ledger import Ledger


class DictStore:
    def __init__(self, data=None):
        self.data = dict(data or {})

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value):
        self.data[key] = value


def test_deposit_adds_to_the_stored_balance():
    async def main():
        store = DictStore({"alice": 100})
        ledger = Ledger(store)
        assert await ledger.deposit("alice", 25) == 125
        assert await ledger.deposit("bob", 10) == 10
        return store.data

    assert asyncio.run(main()) == {"alice": 125, "bob": 10}


def test_deposit_must_be_positive():
    async def main():
        with pytest.raises(ValueError):
            await Ledger(DictStore()).deposit("alice", 0)

    asyncio.run(main())
