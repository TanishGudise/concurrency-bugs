"""Retrying transient database errors."""

from __future__ import annotations

import asyncio
import functools
import logging
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

from members.db import TransientError

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def retry_transient(
    attempts: int = 4, delay_s: float = 0.05
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Retry an async call on `TransientError`, up to `attempts` times in total.

    Only transient errors are retried; anything else (including cancellation) propagates
    immediately, so a cancelled request never keeps retrying in the background.
    """
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    def decorate(call: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(call)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            for attempt in range(1, attempts + 1):
                try:
                    return await call(*args, **kwargs)
                except TransientError:
                    if attempt == attempts:
                        raise
                    logger.warning("%s: transient error (attempt %d)", call.__name__, attempt)
                    if delay_s:
                        await asyncio.sleep(delay_s * attempt)
            raise AssertionError("unreachable")

        return wrapper

    return decorate
