"""Transport to the metrics collector."""

from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

from telemetry.emitter import SendError

Post = Callable[[str, bytes], Awaitable[int]]

_REQUIRED = {"job": str, "metric": str, "value": int, "ts": float}


class InvalidPayload(ValueError):
    pass


def validate_payload(payload: dict[str, Any]) -> None:
    for key, kind in _REQUIRED.items():
        if key not in payload:
            raise InvalidPayload(f"missing field {key!r}")
        if not isinstance(payload[key], kind):
            raise InvalidPayload(f"{key!r} must be {kind.__name__}")
    if isinstance(payload["value"], bool) or payload["value"] < 0:
        raise InvalidPayload("counters are never negative")


class CollectorTransport:
    """Posts counter values. 5xx and connection errors become SendError (retryable)."""

    def __init__(self, post: Post, url: str, *, job: str, metric: str) -> None:
        self._post = post
        self._url = url
        self._job = job
        self._metric = metric

    async def send(self, value: int) -> None:
        payload = {"job": self._job, "metric": self._metric, "value": value, "ts": time.time()}
        validate_payload(payload)
        try:
            status = await self._post(self._url, json.dumps(payload).encode())
        except OSError as exc:
            raise SendError(str(exc)) from exc
        if status >= 500:
            raise SendError(f"collector returned {status}")
        if status >= 400:
            raise InvalidPayload(f"collector rejected the payload: {status}")
