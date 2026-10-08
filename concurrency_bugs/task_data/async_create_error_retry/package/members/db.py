"""Database interface and errors."""

from __future__ import annotations

from typing import Any, Protocol


class TransientError(Exception):
    """Connection reset or failover: the request did not reach the database."""


class ConstraintViolation(Exception):
    """The database rejected the write (duplicate handle, bad data)."""


class MemberDatabase(Protocol):
    async def create_member(self, handle: str) -> dict[str, Any]: ...
    async def count_members(self) -> int: ...


def member_summary(member: dict[str, Any]) -> str:
    joined = member.get("joined", "unknown date")
    return f"@{member['handle']} (joined {joined})"


def merge_profile(member: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Overlay profile fields on a member record without overwriting identity fields."""
    merged = dict(member)
    for key, value in profile.items():
        if key in ("id", "handle"):
            continue
        merged[key] = value
    return merged


class InMemoryMembers:
    """A MemberDatabase for local development and demos."""

    def __init__(self) -> None:
        self._rows: dict[str, dict[str, Any]] = {}

    async def create_member(self, handle: str) -> dict[str, Any]:
        if handle in self._rows:
            raise ConstraintViolation(f"handle {handle!r} is taken")
        row = {"id": len(self._rows) + 1, "handle": handle}
        self._rows[handle] = row
        return row

    async def count_members(self) -> int:
        return len(self._rows)


def page(
    members: list[dict[str, Any]], *, cursor: int = 0, size: int = 50
) -> tuple[list[dict[str, Any]], int | None]:
    """Cursor pagination for member listings: (items, next cursor or None)."""
    if size < 1:
        raise ValueError("size must be at least 1")
    ordered = sorted(members, key=lambda m: m["id"])
    items = [m for m in ordered if m["id"] > cursor][:size]
    next_cursor = items[-1]["id"] if len(items) == size else None
    return items, next_cursor


def search(members: list[dict[str, Any]], prefix: str, *, limit: int = 10) -> list[dict[str, Any]]:
    """Members whose handle starts with ``prefix`` (case-insensitive), shortest handles first."""
    prefix = prefix.strip().lower().lstrip("@")
    hits = [m for m in members if m["handle"].startswith(prefix)]
    return sorted(hits, key=lambda m: (len(m["handle"]), m["handle"]))[:limit]
