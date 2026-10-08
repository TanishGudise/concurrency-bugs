"""Concurrent fetching with a limit on requests in progress."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence

from crawler.ratelimit import HostRateLimiter
from crawler.retry import Backoff, TransientFetchError, with_retries

logger = logging.getLogger(__name__)

Fetch = Callable[[str], Awaitable[bytes]]


async def fetch_all(
    urls: Sequence[str],
    fetch: Fetch,
    limit: int,
    *,
    retries: int = 2,
    backoff: Backoff | None = None,
) -> list[bytes]:
    """Fetch every URL with at most ``limit`` requests in progress; results in input order."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    backoff = backoff or Backoff()

    slots = asyncio.Semaphore(limit)

    async def attempt(url: str) -> bytes:
        async with slots:
            return await fetch(url)

    async def fetch_one(url: str) -> bytes:
        try:
            return await attempt(url)
        except TransientFetchError:
            if retries == 0:
                raise
            logger.info("retrying %s", url)
        # Retry outside the concurrency slot, so a flaky host doesn't hold it during backoff.
        return await with_retries(lambda: fetch(url), attempts=retries, backoff=backoff)

    return list(await asyncio.gather(*(fetch_one(url) for url in urls)))


class Crawler:
    """Crawls a frontier of URLs in batches, politely."""

    def __init__(self, fetch: Fetch, *, limit: int = 5, rate_limiter: HostRateLimiter | None = None) -> None:
        self._fetch = fetch
        self._limit = limit
        self._rate_limiter = rate_limiter or HostRateLimiter()
        self.pages: dict[str, bytes] = {}

    async def _polite_fetch(self, url: str) -> bytes:
        await self._rate_limiter.acquire(url)
        return await self._fetch(url)

    async def crawl(self, frontier: Sequence[str], *, batch_size: int = 50) -> dict[str, bytes]:
        pending = [url for url in dict.fromkeys(frontier) if url not in self.pages]
        for start in range(0, len(pending), batch_size):
            batch = pending[start : start + batch_size]
            bodies = await fetch_all(batch, self._polite_fetch, self._limit)
            self.pages.update(zip(batch, bodies, strict=True))
        return self.pages
