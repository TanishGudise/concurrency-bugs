"""Bank accounts shared between worker threads."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass(eq=False)
class Account:
    id: int
    balance: int
    lock: Any = field(default_factory=threading.Lock, repr=False)


class InsufficientFunds(Exception):
    pass


def _in_lock_order(accounts: list[Account]) -> list[Account]:
    # Every code path takes account locks in ascending id order. With one global order a
    # cycle of "holds X, waits for Y" is impossible, so no deadlock can form.
    return sorted(accounts, key=lambda account: account.id)


class Bank:
    def __init__(self, accounts: list[Account]) -> None:
        self._accounts = list(accounts)

    def transfer(self, src: Account, dst: Account, amount: int) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        if src is dst:
            raise ValueError("cannot transfer to the same account")
        first, second = _in_lock_order([src, dst])
        with first.lock:
            with second.lock:
                if src.balance < amount:
                    raise InsufficientFunds(f"account {src.id} has {src.balance}, needs {amount}")
                src.balance -= amount
                dst.balance += amount

    def total(self) -> int:
        """Sum of all balances, as a consistent snapshot."""
        ordered = _in_lock_order(self._accounts)
        for account in ordered:
            account.lock.acquire()
        try:
            return sum(account.balance for account in ordered)
        finally:
            for account in reversed(ordered):
                account.lock.release()
