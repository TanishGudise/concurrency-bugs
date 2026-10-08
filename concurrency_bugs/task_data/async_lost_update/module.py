"""Account balances kept in a shared key-value store."""

from __future__ import annotations

from typing import Protocol


class Store(Protocol):
    async def get(self, key: str) -> int | None: ...
    async def set(self, key: str, value: int) -> None: ...


class Ledger:
    """Balances live in ``store``, which other services read and write too."""

    def __init__(self, store: Store) -> None:
        self._store = store

    async def balance(self, account: str) -> int:
        return await self._store.get(account) or 0

    async def deposit(self, account: str, amount: int) -> int:
        """Add ``amount`` to ``account`` and return the new balance."""
        if amount <= 0:
            raise ValueError("amount must be positive")
        current = await self._store.get(account) or 0
        new_balance = current + amount
        await self._store.set(account, new_balance)
        return new_balance
