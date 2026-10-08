"""Topic patterns: dotted names with `*` (exactly one segment) and `#` (zero or more)."""

from __future__ import annotations

import functools
import re


@functools.lru_cache(maxsize=1024)
def compile_pattern(pattern: str) -> re.Pattern[str]:
    if not pattern or pattern.startswith(".") or pattern.endswith(".") or ".." in pattern:
        raise ValueError(f"invalid topic pattern: {pattern!r}")
    parts = []
    for segment in pattern.split("."):
        if segment == "*":
            parts.append(r"[^.]+")
        elif segment == "#":
            parts.append(r".*")
        elif "*" in segment or "#" in segment:
            raise ValueError(f"wildcards must be whole segments: {pattern!r}")
        else:
            parts.append(re.escape(segment))
    regex = r"\.".join(parts)
    # `a.#` should also match `a` itself.
    regex = regex.replace(r"\..*", r"(?:\..*)?")
    return re.compile(rf"^{regex}$")


def matches(pattern: str, topic: str) -> bool:
    return compile_pattern(pattern).match(topic) is not None
