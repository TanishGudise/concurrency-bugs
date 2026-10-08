"""How long and how often to retry a send."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """`budget_s` is the total time allowed for one send across all its attempts. 0 means "don't
    retry". `attempt_timeout_s` caps any single attempt."""

    budget_s: float = 30.0
    attempts: int = 3
    attempt_timeout_s: float = 10.0

    def __post_init__(self) -> None:
        if self.budget_s < 0:
            raise ValueError("budget_s must not be negative")
        if self.attempts < 1:
            raise ValueError("attempts must be at least 1")
        if self.attempt_timeout_s <= 0:
            raise ValueError("attempt_timeout_s must be positive")

    def attempt_timeouts(self) -> list[float]:
        """The timeout of each attempt, in order."""
        if self.budget_s == 0:
            return [3600.0]  # no budget limit: effectively no timeout
        per_attempt = min(self.attempt_timeout_s, self.budget_s / self.attempts)
        return [max(per_attempt, 0.001)] * self.attempts

    def describe(self) -> str:
        timeouts = self.attempt_timeouts()
        return f"{len(timeouts)} attempt(s) of up to {timeouts[0]:g}s each"
