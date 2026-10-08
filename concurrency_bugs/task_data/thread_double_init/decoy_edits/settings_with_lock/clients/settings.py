"""Settings from the environment, and a config source built on them."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Settings:
    database_url: str
    cache_url: str
    pool_size: int
    timeout_s: float


_settings: Settings | None = None
_settings_lock = threading.Lock()


def load_settings() -> Settings:
    """Read settings once per process."""
    global _settings
    with _settings_lock:
        if _settings is None:
            _settings = _read_settings()
        return _settings


def _read_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("DATABASE_URL", "postgres://localhost/app"),
        cache_url=os.environ.get("CACHE_URL", "redis://localhost:6379/0"),
        pool_size=int(os.environ.get("POOL_SIZE", "10")),
        timeout_s=float(os.environ.get("CLIENT_TIMEOUT_S", "5")),
    )


class EnvConfig:
    """A ConfigSource that serves client options from environment settings."""

    def options_for(self, name: str) -> dict[str, Any]:
        settings = load_settings()
        options: dict[str, Any] = {"timeout_s": settings.timeout_s}
        if name == "db":
            options.update(url=settings.database_url, pool_size=settings.pool_size)
        elif name == "cache":
            options.update(url=settings.cache_url)
        return options


def redact(url: str) -> str:
    """Hide the password in a connection URL before logging it."""
    scheme, sep, rest = url.partition("://")
    if not sep or "@" not in rest:
        return url
    credentials, _, host = rest.rpartition("@")
    user = credentials.split(":", 1)[0]
    return f"{scheme}://{user}:***@{host}"


class ClientHealth:
    """Tracks the last health-check result per client, for the /healthz endpoint.

    Health checks run on a background thread while request threads read the status, so the
    status map is guarded by a lock. The lock is never held while a check runs.
    """

    def __init__(self) -> None:
        self._status: dict[str, tuple[bool, str]] = {}
        self._lock = threading.Lock()

    def record(self, name: str, ok: bool, detail: str = "") -> None:
        with self._lock:
            self._status[name] = (ok, detail)

    def snapshot(self) -> dict[str, tuple[bool, str]]:
        with self._lock:
            return dict(self._status)

    def healthy(self) -> bool:
        return all(ok for ok, _ in self.snapshot().values())
