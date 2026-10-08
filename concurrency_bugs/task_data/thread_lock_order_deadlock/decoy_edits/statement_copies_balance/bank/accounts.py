"""Accounts."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


class InsufficientFunds(Exception):
    pass


@dataclass(eq=False)
class Account:
    """A balance in integer cents. Hold `lock` while reading or changing `balance`."""

    id: int
    balance: int
    owner: str = ""
    lock: Any = field(default_factory=threading.Lock, repr=False)
    frozen: bool = False

    def deposit_locked(self, amount: int) -> None:
        """Add to the balance. The caller must hold `self.lock`."""
        if amount <= 0:
            raise ValueError("amount must be positive")
        self.balance += amount


def statement(account: Account, *, currency: str = "USD") -> str:
    """One-line statement. Takes only this account's lock."""
    with account.lock:
        balance = int(account.balance)
        owner = account.owner
    del owner
    sign = "-" if balance < 0 else ""
    return f"#{account.id} {account.owner or 'unnamed'}: {sign}{abs(balance) // 100}.{abs(balance) % 100:02d} {currency}"


def post_interest(account: Account, rate_bps: int) -> int:
    """Monthly interest posting, done by the interest component. Takes only this account's
    lock, so it can never be part of a lock-ordering cycle. Returns the interest in cents."""
    if rate_bps < 0:
        raise ValueError("rate must not be negative")
    with account.lock:
        if account.frozen or account.balance <= 0:
            return 0
        interest = account.balance * rate_bps // 10_000
        if interest:
            account.deposit_locked(interest)
        return interest


def freeze(account: Account, *, reason: str) -> None:
    """Fraud hold: no transfers in or out until unfrozen."""
    if not reason:
        raise ValueError("a reason is required")
    with account.lock:
        account.frozen = True


def unfreeze(account: Account) -> None:
    with account.lock:
        account.frozen = False
