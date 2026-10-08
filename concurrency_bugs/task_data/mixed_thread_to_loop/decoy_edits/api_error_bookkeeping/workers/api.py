"""Batch processing facade."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from workers.runner import JobRunner


@dataclass
class BatchResult:
    ok: dict[str, Any] = field(default_factory=dict)
    failed: dict[str, BaseException] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        total = len(self.ok) + len(self.failed)
        return len(self.ok) / total if total else 1.0


class BatchApi:
    """Processes named items with a blocking function, at most `concurrency` at a time."""

    def __init__(self, runner: JobRunner, *, concurrency: int = 8) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be at least 1")
        self._runner = runner
        self._slots = asyncio.Semaphore(concurrency)

    async def _one(self, fn: Callable[[Any], Any], name: str, item: Any, result: BatchResult) -> None:
        async with self._slots:
            try:
                value = await self._runner.run(fn, item)
            except Exception as exc:
                result.failed[name] = exc
            else:
                result.ok[name] = value

    async def process(self, fn: Callable[[Any], Any], items: dict[str, Any]) -> BatchResult:
        result = BatchResult()
        await asyncio.gather(*(self._one(fn, name, item, result) for name, item in items.items()))
        return result


def chunked(items: dict[str, Any], size: int) -> list[dict[str, Any]]:
    """Split a batch into smaller batches of at most ``size`` items, keeping order."""
    if size < 1:
        raise ValueError("size must be at least 1")
    names = list(items)
    return [{name: items[name] for name in names[i : i + size]} for i in range(0, len(names), size)]


async def process_with_retry(
    api: BatchApi, fn: Callable[[Any], Any], items: dict[str, Any], *, attempts: int = 2
) -> BatchResult:
    """Process a batch, then re-run only the failed items, up to ``attempts`` rounds in total."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    final = BatchResult()
    pending = dict(items)
    for _ in range(attempts):
        result = await api.process(fn, pending)
        final.ok.update(result.ok)
        final.failed = dict(result.failed)
        pending = {name: items[name] for name in result.failed}
        if not pending:
            break
    return final
