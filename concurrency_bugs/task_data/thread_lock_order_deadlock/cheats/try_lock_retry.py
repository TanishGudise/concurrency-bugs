"""Bank accounts shared between worker threads."""

from __future__ import annotations

import random
import threading
import time
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
        while True:
            src.lock.acquire()
            if dst.lock.acquire(timeout=0.05):
                break
            src.lock.release()  # back off and retry instead of deadlocking
            time.sleep(random.uniform(0, 0.01))
        try:
            if src.balance < amount:
                raise InsufficientFunds(f"account {src.id} has {src.balance}, needs {amount}")
            src.balance -= amount
            dst.balance += amount
        finally:
            dst.lock.release()
            src.lock.release()

    def total(self) -> int:
        """Sum of all balances, as a consistent snapshot."""
        while True:
            held = []
            for account in self._accounts:
                if not account.lock.acquire(timeout=0.05):
                    break
                held.append(account)
            if len(held) == len(self._accounts):
                break
            for account in reversed(held):
                account.lock.release()
            time.sleep(random.uniform(0, 0.01))
        try:
            return sum(account.balance for account in self._accounts)
        finally:
            for account in reversed(self._accounts):
                account.lock.release()
