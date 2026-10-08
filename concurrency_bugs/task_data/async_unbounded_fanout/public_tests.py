import asyncio

import pytest
from fetcher import fetch_all


async def fake_fetch(url):
    return url.upper().encode()


def test_results_are_in_input_order():
    urls = ["a", "b", "c", "d"]
    assert asyncio.run(fetch_all(urls, fake_fetch, limit=2)) == [b"A", b"B", b"C", b"D"]


def test_limit_must_be_positive():
    with pytest.raises(ValueError):
        asyncio.run(fetch_all(["a"], fake_fetch, limit=0))
