import asyncio

import pytest
from sandbox import Frame, RemoteProcess, RetryPolicy, StdinWriter, decode_frame, encode_frame


class RecordingChannel:
    def __init__(self):
        self.frames = []

    async def send(self, frame, *, timeout):
        self.frames.append(frame)


def test_writes_then_end_of_input():
    async def main():
        channel = RecordingChannel()
        writer = StdinWriter(channel)
        await writer.write(b"hello ")
        await writer.write(b"")
        await writer.write(b"world")
        await writer.close()
        await writer.close()  # closing twice is fine
        with pytest.raises(ValueError):
            await writer.write(b"more")
        return channel.frames, writer.bytes_written

    frames, written = asyncio.run(main())
    assert [f.payload for f in frames] == [b"hello ", b"world", b""]
    assert [f.seq for f in frames] == [0, 1, 2] and written == 11


def test_policy_splits_the_budget():
    assert RetryPolicy(budget_s=30, attempts=3, attempt_timeout_s=10).attempt_timeouts() == [10, 10, 10]
    assert RetryPolicy(budget_s=6, attempts=3, attempt_timeout_s=10).attempt_timeouts() == [2, 2, 2]
    with pytest.raises(ValueError):
        RetryPolicy(attempts=0)


def test_frame_encoding_round_trips():
    data = encode_frame(Frame(7, b"abc")) + encode_frame(Frame(8, b""))
    first, rest = decode_frame(data)
    second, rest = decode_frame(rest)
    assert (first, second, rest) == (Frame(7, b"abc"), Frame(8, b""), b"")


def test_process_exit_code():
    process = RemoteProcess(42, stdin=None)
    process.mark_exited(0)
    assert not process.running and process.exit_code == 0
