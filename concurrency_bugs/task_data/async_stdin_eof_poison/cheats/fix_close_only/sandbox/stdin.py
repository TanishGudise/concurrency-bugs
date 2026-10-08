"""Streaming a remote process's standard input."""

from __future__ import annotations

import logging

from sandbox.channel import Channel, ChannelError, ChannelTimeout, Frame
from sandbox.retry import RetryPolicy

logger = logging.getLogger(__name__)


class StdinWriter:
    """Writes data frames, then an empty end-of-input frame on `close()`."""

    def __init__(self, channel: Channel, policy: RetryPolicy | None = None) -> None:
        self._channel = channel
        self._policy = policy or RetryPolicy()
        self._next_seq = 0
        self._failed = False
        self._closed = False
        self.bytes_written = 0

    @property
    def closed(self) -> bool:
        return self._closed

    async def write(self, data: bytes) -> None:
        if self._closed:
            raise ValueError("stdin is closed")
        if not data:
            return  # nothing to send; end-of-input is close()'s job
        if self._failed:
            return  # the stream is broken and the caller already saw the error
        await self._send(Frame(self._take_seq(), bytes(data)))
        self.bytes_written += len(data)

    async def close(self) -> None:
        """Tell the remote process there is no more input."""
        if self._closed:
            return
        await self._send(Frame(self._take_seq(), b""))
        self._closed = True

    def _take_seq(self) -> int:
        seq = self._next_seq
        self._next_seq += 1
        return seq

    async def _send(self, frame: Frame) -> None:
        timeouts = self._policy.attempt_timeouts()
        for attempt, timeout in enumerate(timeouts, start=1):
            try:
                await self._channel.send(frame, timeout=timeout)
                return
            except ChannelTimeout:
                # The frame may have arrived; resending the same sequence number is safe.
                if attempt == len(timeouts):
                    self._failed = True
                    raise
                logger.warning("frame %d: no ack within %.3fs (attempt %d)", frame.seq, timeout, attempt)
            except ChannelError:
                self._failed = True
                raise
