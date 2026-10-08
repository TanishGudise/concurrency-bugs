"""Lazily created shared client."""

from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class LazyClient(Generic[T]):
    """Creates the client on first use with ``factory`` (slow: it opens network connections)."""

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._client: T | None = factory()  # create up front: no race possible

    def get(self) -> T:
        if self._client is None:
            self._client = self._factory()
        return self._client
