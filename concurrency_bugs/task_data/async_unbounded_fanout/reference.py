"""Concurrent fetching with a limit on requests in flight."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence


async def fetch_all(
    urls: Sequence[str],
    fetch: Callable[[str], Awaitable[bytes]],
    limit: int,
) -> list[bytes]:
    """Fetch every URL with at most ``limit`` requests in flight; results in input order."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    # One semaphore shared by every fetch. A semaphore created per fetch limits nothing.
    slots = asyncio.Semaphore(limit)

    async def fetch_one(url: str) -> bytes:
        async with slots:
            return await fetch(url)

    return list(await asyncio.gather(*(fetch_one(url) for url in urls)))
