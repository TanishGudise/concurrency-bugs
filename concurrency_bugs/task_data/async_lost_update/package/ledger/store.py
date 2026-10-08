"""Key-value store client."""

from __future__ import annotations

from collections import Counter
from typing import Protocol

# Request counters for the metrics endpoint. Everything runs on the event loop thread, so
# plain increments are safe here.
STATS: Counter[str] = Counter()


class Store(Protocol):
    async def get(self, key: str) -> int | None: ...
    async def set(self, key: str, value: int) -> None: ...


class NamespacedStore:
    """Prefixes keys so several services can share one store, and validates values."""

    def __init__(self, inner: Store, namespace: str) -> None:
        if not namespace or ":" in namespace:
            raise ValueError("namespace must be non-empty and contain no ':'")
        self._inner = inner
        self._prefix = f"{namespace}:"

    def _key(self, account: str) -> str:
        if not account or any(ch.isspace() for ch in account):
            raise ValueError(f"invalid account id: {account!r}")
        return self._prefix + account

    async def get(self, key: str) -> int | None:
        STATS["get"] += 1
        return await self._inner.get(self._key(key))

    async def set(self, key: str, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError("balances are stored as integer cents")
        STATS["set"] += 1
        await self._inner.set(self._key(key), value)


class TransientStoreError(Exception):
    """The store was briefly unavailable (failover, connection reset)."""


class RetryingStore:
    """Retries transient store errors. Reads are safe to retry; a write is retried only if
    the store reports it was not applied (TransientStoreError is raised before applying)."""

    def __init__(self, inner: Store, *, attempts: int = 3) -> None:
        if attempts < 1:
            raise ValueError("attempts must be at least 1")
        self._inner = inner
        self._attempts = attempts
        self.retries = 0

    async def get(self, key: str) -> int | None:
        for attempt in range(1, self._attempts + 1):
            try:
                return await self._inner.get(key)
            except TransientStoreError:
                if attempt == self._attempts:
                    raise
                self.retries += 1
        raise AssertionError("unreachable")

    async def set(self, key: str, value: int) -> None:
        for attempt in range(1, self._attempts + 1):
            try:
                await self._inner.set(key, value)
                return
            except TransientStoreError:
                if attempt == self._attempts:
                    raise
                self.retries += 1


async def export_balances(store: Store, accounts: list[str]) -> dict[str, int]:
    """Read many balances for a report. Not a consistent snapshot: use for display only."""
    return {account: await store.get(account) or 0 for account in accounts}
