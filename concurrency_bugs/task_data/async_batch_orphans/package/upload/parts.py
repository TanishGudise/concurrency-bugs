"""Splitting a payload into parts."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

MIN_PART_SIZE = 5
MAX_PARTS = 10_000


@dataclass(frozen=True)
class Part:
    index: int
    offset: int
    data: bytes

    @property
    def size(self) -> int:
        return len(self.data)


def etag(data: bytes) -> str:
    """Storage-style etag: hex MD5 of the bytes, quoted."""
    return f'"{hashlib.md5(data).hexdigest()}"'


def split_parts(payload: bytes, part_size: int) -> list[Part]:
    """Cut ``payload`` into parts of ``part_size`` bytes (the last one may be smaller)."""
    if part_size < MIN_PART_SIZE:
        raise ValueError(f"part_size must be at least {MIN_PART_SIZE}")
    parts = [
        Part(index, offset, payload[offset : offset + part_size])
        for index, offset in enumerate(range(0, len(payload), part_size))
    ]
    if len(parts) > MAX_PARTS:
        raise ValueError("too many parts; use a larger part_size")
    return parts or [Part(0, 0, b"")]


def combined_etag(etags: list[str]) -> str:
    """Etag of a completed multipart upload: MD5 of the part digests, plus the part count."""
    digests = b"".join(bytes.fromhex(tag.strip('"')) for tag in etags)
    return f'"{hashlib.md5(digests).hexdigest()}-{len(etags)}"'


@dataclass(frozen=True)
class Manifest:
    """What a resumable upload has finished so far: part index -> etag."""

    total_parts: int
    done: dict[int, str]

    @property
    def remaining(self) -> list[int]:
        return [i for i in range(self.total_parts) if i not in self.done]

    @property
    def complete(self) -> bool:
        return not self.remaining


def resume(parts: list[Part], manifest: Manifest) -> list[Part]:
    """The parts still to upload, after checking the manifest matches this payload."""
    if manifest.total_parts != len(parts):
        raise ValueError("manifest is for a different payload (part count differs)")
    for index, tag in manifest.done.items():
        if etag(parts[index].data) != tag:
            raise ValueError(f"part {index} changed since it was uploaded")
    return [parts[i] for i in manifest.remaining]


def record(manifest: Manifest, part: Part, tag: str) -> Manifest:
    done = dict(manifest.done)
    done[part.index] = tag
    return Manifest(manifest.total_parts, done)
