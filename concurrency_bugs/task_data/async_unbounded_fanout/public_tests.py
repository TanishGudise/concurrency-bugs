import asyncio

import pytest
from crawler import Backoff, Crawler, HostRateLimiter, TransientFetchError, fetch_all

NO_WAIT = Backoff(base_s=0, jitter=0)


async def fake_fetch(url):
    return url.upper().encode()


def test_results_are_in_input_order():
    urls = ["a", "b", "c", "d"]
    assert asyncio.run(fetch_all(urls, fake_fetch, limit=2)) == [b"A", b"B", b"C", b"D"]


def test_limit_must_be_positive():
    with pytest.raises(ValueError):
        asyncio.run(fetch_all(["a"], fake_fetch, limit=0))


def test_transient_failures_are_retried():
    failures = {"b": 1}

    async def flaky(url):
        if failures.get(url, 0) > 0:
            failures[url] -= 1
            raise TransientFetchError(url)
        return url.encode()

    assert asyncio.run(fetch_all(["a", "b"], flaky, limit=2, retries=2, backoff=NO_WAIT)) == [b"a", b"b"]


def test_crawler_fetches_each_page_once():
    async def main():
        crawler = Crawler(fake_fetch, rate_limiter=HostRateLimiter(rate=1000, burst=100))
        return await crawler.crawl(["http://x/a", "http://x/b", "http://x/a"])

    assert sorted(asyncio.run(main())) == ["http://x/a", "http://x/b"]
