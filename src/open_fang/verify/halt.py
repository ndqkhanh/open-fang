"""ConfidenceMonitor (v6.1) — ReBalance-inspired halt signal.

Tracks a rolling window of LLM judge verdicts and their confidence levels.
Emits a `should_halt()` signal when:
    - The last N verdicts (default N=3) all agree on `supported` verdict, AND
    - Each verdict's confidence is ≥ threshold (default 0.85).

When the halt fires, the pipeline can skip the critic and cross-model tiers
for the claim. Tier 1-3 always run regardless.

Opt-in: pipeline defaults to halt=None (no skip). Wire a monitor to activate.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class VerdictObservation:
    claim_id: str
    supported: bool
    confidence: float


@dataclass
class ConfidenceMonitor:
    window: int = 3
    threshold: float = 0.85
    recent: deque = field(default_factory=deque)
    halts_fired: int = 0

    def observe(self, claim_id: str, supported: bool, confidence: float) -> None:
        self.recent.append(VerdictObservation(claim_id=claim_id, supported=supported, confidence=confidence))
        while len(self.recent) > self.window:
            self.recent.popleft()

    def should_halt(self) -> bool:
        if len(self.recent) < self.window:
            return False
        first = self.recent[0]
        if any(obs.supported != first.supported for obs in self.recent):
            return False
        if any(obs.confidence < self.threshold for obs in self.recent):
            return False
        self.halts_fired += 1
        return True

    def reset(self) -> None:
        self.recent.clear()

    def stats(self) -> dict:
        return {
            "window": self.window,
            "threshold": self.threshold,
            "current_window_size": len(self.recent),
            "halts_fired": self.halts_fired,
        }
