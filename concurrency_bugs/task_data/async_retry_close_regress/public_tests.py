import asyncio
import random

import pytest
from telemetry import Backoff, CollectorTransport, InvalidPayload, MetricEmitter, SendError


class RecordingTransport:
    def __init__(self, failures=0):
        self.sent = []
        self.failures = failures

    async def send(self, value):
        if self.failures:
            self.failures -= 1
            raise SendError("collector unavailable")
        self.sent.append(value)


NO_WAIT = Backoff(base_s=0, cap_s=0)


def test_final_value_is_delivered():
    async def main():
        transport = RecordingTransport()
        async with MetricEmitter(transport, NO_WAIT) as emitter:
            for n in (10, 20, 30):
                emitter.report(n)
        return transport.sent

    sent = asyncio.run(main())
    assert sent[-1] == 30 and sent == sorted(sent)


def test_failed_sends_are_retried():
    async def main():
        transport = RecordingTransport(failures=2)
        async with MetricEmitter(transport, NO_WAIT) as emitter:
            emitter.report(7)
        return transport.sent, emitter.failures

    assert asyncio.run(main()) == ([7], 2)


def test_backoff_is_bounded():
    backoff = Backoff(base_s=1, cap_s=4, rng=random.Random(0))
    assert all(0 <= backoff.delay(n) <= 4 for n in range(1, 10))


def test_collector_transport_maps_errors():
    async def post(url, body):
        return 503

    transport = CollectorTransport(post, "http://collector", job="j1", metric="rows")
    with pytest.raises(SendError):
        asyncio.run(transport.send(5))
    with pytest.raises(InvalidPayload):
        asyncio.run(transport.send(-1))
