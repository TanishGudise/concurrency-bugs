"""Name -> LazyClient registry shared by all request threads."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any, Protocol

from clients.lazy import LazyClient


class UnknownClient(KeyError):
    pass


class ConfigSource(Protocol):
    def options_for(self, name: str) -> dict[str, Any]: ...


class ClientRegistry:
    def __init__(self, factories: dict[str, Callable[..., Any]], config: ConfigSource) -> None:
        self._factories = dict(factories)
        self._config = config
        self._clients: dict[str, LazyClient[Any]] = {}
        # Guards _clients only. It is never held while a client's factory runs, so one
        # client's slow creation can't delay a different client.
        self._lock = threading.RLock()

    def names(self) -> list[str]:
        return sorted(self._factories)

    def lazy(self, name: str) -> LazyClient[Any]:
        """The LazyClient for ``name``, created on first request."""
        with self._lock:
            client = self._clients.get(name)
            if client is None:
                if name not in self._factories:
                    raise UnknownClient(name)
                options = self._config.options_for(name)
                client = LazyClient(self._factories[name], name=name, options=options)
                self._clients[name] = client
            return client

    def get(self, name: str) -> Any:
        """The ready-to-use client for ``name``."""
        with self._lock:  # hold the registry lock until the client is ready
            return self.lazy(name).get()

    def ready(self) -> dict[str, bool]:
        return {name: client.ready for name, client in self._clients.items()}
