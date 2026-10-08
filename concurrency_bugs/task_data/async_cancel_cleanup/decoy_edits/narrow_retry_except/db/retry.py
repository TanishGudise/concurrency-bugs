"""Retrying idempotent reads on connection errors."""

from __future__ import annotations

import functools
import logging
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class ConnectionLost(Exception):
    """The connection dropped before the query was sent. Safe to retry."""


def retry_on(
    *errors: type[Exception], attempts: int = 2
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Retry an async call when it raises one of `errors`.

    The except clause catches `Exception`, never `BaseException`, so cancellation is not
    caught and always propagates.
    """

    def decorate(call: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(call)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return await call(*args, **kwargs)
                except errors as exc:
                    last = exc
                    logger.warning("%s failed (attempt %d): %s", call.__name__, attempt, exc)
            assert last is not None
            raise last

        return wrapper

    return decorate
