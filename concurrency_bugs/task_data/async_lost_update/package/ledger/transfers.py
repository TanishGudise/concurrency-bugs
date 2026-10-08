"""Moving money between two accounts."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from ledger.ledger import InsufficientFunds, Ledger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TransferReceipt:
    src: str
    dst: str
    amount: int
    src_balance: int
    dst_balance: int
    id: str = field(default_factory=lambda: uuid.uuid4().hex)


async def transfer(ledger: Ledger, src: str, dst: str, amount: int) -> TransferReceipt:
    """Move ``amount`` cents from ``src`` to ``dst``, all or nothing."""
    if amount <= 0:
        raise ValueError("amount must be positive")
    if src == dst:
        raise ValueError("cannot transfer to the same account")
    src_balance = await ledger._read(src)
    if src_balance < amount:
        raise InsufficientFunds(f"{src} has {src_balance}, needs {amount}")
    dst_balance = await ledger._read(dst)
    await ledger._write(src, src_balance - amount, -amount)
    await ledger._write(dst, dst_balance + amount, amount)
    logger.info("transferred %d from %s to %s", amount, src, dst)
    return TransferReceipt(src, dst, amount, src_balance - amount, dst_balance + amount)
