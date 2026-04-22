"""Node-local retry policy with exponential backoff."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_s: float = 0.5
    factor: float = 2.0

    def delay_for_attempt(self, attempt: int) -> float:
        return self.base_delay_s * (self.factor ** max(0, attempt - 1))
