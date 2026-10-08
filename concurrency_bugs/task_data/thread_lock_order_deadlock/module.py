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


class Bank:
    def __init__(self, accounts: list[Account]) -> None:
        self._accounts = list(accounts)

    def transfer(self, src: Account, dst: Account, amount: int) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        if src is dst:
            raise ValueError("cannot transfer to the same account")
        with src.lock:
            with dst.lock:
                if src.balance < amount:
                    raise InsufficientFunds(f"account {src.id} has {src.balance}, needs {amount}")
                src.balance -= amount
                dst.balance += amount

    def total(self) -> int:
        """Sum of all balances, as a consistent snapshot."""
        for account in self._accounts:
            account.lock.acquire()
        try:
            return sum(account.balance for account in self._accounts)
        finally:
            for account in reversed(self._accounts):
                account.lock.release()
