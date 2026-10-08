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
        self._cache: dict[str, int] = {}

    async def balance(self, account: str) -> int:
        return await self._store.get(account) or 0

    async def deposit(self, account: str, amount: int) -> int:
        """Add ``amount`` to ``account`` and return the new balance."""
        if amount <= 0:
            raise ValueError("amount must be positive")
        if account not in self._cache:
            stored = await self._store.get(account) or 0
            self._cache.setdefault(account, stored)
        self._cache[account] += amount  # no await between read and write
        new_balance = self._cache[account]
        await self._store.set(account, new_balance)
        return new_balance
