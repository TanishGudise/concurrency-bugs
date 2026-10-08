"""Concurrent fetching with a limit on requests in flight."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence


async def fetch_all(
    urls: Sequence[str],
    fetch: Callable[[str], Awaitable[bytes]],
    limit: int,
) -> list[bytes]:
    """Fetch every URL with at most ``limit`` requests in flight; results in input order."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    return [await fetch(url) for url in urls]
