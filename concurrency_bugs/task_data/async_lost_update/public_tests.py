import asyncio

import pytest
from ledger import InsufficientFunds, Ledger, NamespacedStore, transfer


class DictStore:
    def __init__(self, data=None):
        self.data = dict(data or {})

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value):
        self.data[key] = value


def test_deposit_and_withdraw():
    async def main():
        store = DictStore({"alice": 100})
        ledger = Ledger(store)
        assert await ledger.deposit("alice", 25) == 125
        assert await ledger.withdraw("alice", 5) == 120
        with pytest.raises(InsufficientFunds):
            await ledger.withdraw("alice", 1000)
        return store.data

    assert asyncio.run(main()) == {"alice": 120}


def test_transfer_moves_money():
    async def main():
        store = DictStore({"alice": 100, "bob": 0})
        ledger = Ledger(store)
        receipt = await transfer(ledger, "alice", "bob", 30)
        assert (receipt.src_balance, receipt.dst_balance) == (70, 30)
        with pytest.raises(InsufficientFunds):
            await transfer(ledger, "bob", "alice", 31)
        return store.data

    assert asyncio.run(main()) == {"alice": 70, "bob": 30}


def test_namespaced_store_prefixes_keys():
    async def main():
        inner = DictStore()
        store = NamespacedStore(inner, "ledger")
        await Ledger(store).deposit("alice", 5)
        return inner.data

    assert asyncio.run(main()) == {"ledger:alice": 5}
