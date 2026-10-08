"""HTTP transport for the progress dashboard."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable

Post = Callable[[str, bytes], Awaitable[int]]
"""An async HTTP POST: (url, body) -> status code."""


class DashboardError(Exception):
    pass


class HttpTransport:
    """Sends progress updates for one job to the dashboard API.

    The dashboard rejects concurrent updates for the same job, so sends are serialized with a
    lock. Transient 5xx responses are retried a few times before giving up.
    """

    RETRIES = 3

    def __init__(self, post: Post, base_url: str, job_id: str) -> None:
        self._post = post
        self._url = f"{base_url.rstrip('/')}/jobs/{job_id}/progress"
        self._job_id = job_id
        self._lock = asyncio.Lock()
        self._sequence = 0

    def _body(self, value: float) -> bytes:
        self._sequence += 1
        payload = {
            "job": self._job_id,
            "progress": round(float(value), 4),
            "sequence": self._sequence,
            "sent_at": time.time(),
        }
        return json.dumps(payload, separators=(",", ":")).encode()

    async def send(self, value: float) -> None:
        async with self._lock:
            body = self._body(value)
            for attempt in range(1, self.RETRIES + 1):
                status = await self._post(self._url, body)
                if status < 500:
                    break
                if attempt == self.RETRIES:
                    raise DashboardError(f"dashboard returned {status} after {attempt} attempts")
            if status >= 400:
                raise DashboardError(f"dashboard rejected update: {status}")

    @property
    def sent(self) -> int:
        return self._sequence
