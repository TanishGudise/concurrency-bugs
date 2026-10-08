"""Framed channel to a remote sandbox, and the process handle built on it."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Protocol

_HEADER = struct.Struct("!QI")  # sequence number, payload length


class ChannelError(Exception):
    """The frame was not delivered (connection refused, sandbox gone)."""


class ChannelTimeout(ChannelError):
    """No acknowledgement in time. The frame may or may not have been delivered."""


@dataclass(frozen=True)
class Frame:
    seq: int
    payload: bytes

    @property
    def is_eof(self) -> bool:
        return not self.payload


class Channel(Protocol):
    async def send(self, frame: Frame, *, timeout: float) -> None:
        """Deliver ``frame`` and wait for the remote acknowledgement, up to ``timeout`` seconds."""
        ...


def encode_frame(frame: Frame) -> bytes:
    return _HEADER.pack(frame.seq, len(frame.payload)) + frame.payload


def decode_frame(data: bytes) -> tuple[Frame, bytes]:
    """Decode one frame from the front of ``data``; return it and the remaining bytes."""
    if len(data) < _HEADER.size:
        raise ValueError("incomplete frame header")
    seq, length = _HEADER.unpack_from(data)
    end = _HEADER.size + length
    if len(data) < end:
        raise ValueError("incomplete frame payload")
    return Frame(seq, bytes(data[_HEADER.size : end])), data[end:]


class RemoteProcess:
    """A process in a sandbox: its stdin writer and, once known, its exit code."""

    def __init__(self, pid: int, stdin: object) -> None:
        self.pid = pid
        self.stdin = stdin
        self.exit_code: int | None = None

    def mark_exited(self, code: int) -> None:
        if self.exit_code is not None and self.exit_code != code:
            raise ValueError(f"process {self.pid} already exited with {self.exit_code}")
        self.exit_code = code

    @property
    def running(self) -> bool:
        return self.exit_code is None
