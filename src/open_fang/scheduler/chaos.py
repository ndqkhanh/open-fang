"""Scheduler-level chaos hooks — env-configured fault injection.

Activation: set `OPENFANG_CHAOS_MODE` to a semicolon-delimited list of rules:
    OPENFANG_CHAOS_MODE=network_drop:0.2;memory_drop:0.1

Each rule is `<kind>:<probability>`. Recognized kinds:
    network_drop    — random RuntimeError on any external source.search() call
    memory_drop     — random empty list return from a KB search
    compaction_loss — random FANG.md load returning an empty string

Deterministic in tests via an injectable `random.Random`. The injector is
a thin wrapper that the scheduler + KB + memory modules consult.
"""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field


@dataclass
class ChaosRule:
    kind: str
    probability: float


@dataclass
class ChaosInjector:
    rules: list[ChaosRule] = field(default_factory=list)
    rng: random.Random = field(default_factory=random.Random)

    @classmethod
    def from_env(cls, value: str | None = None, *, rng: random.Random | None = None) -> ChaosInjector:
        raw = value if value is not None else os.environ.get("OPENFANG_CHAOS_MODE", "")
        return cls(rules=_parse_rules(raw), rng=rng or random.Random())

    def probability(self, kind: str) -> float:
        for rule in self.rules:
            if rule.kind == kind:
                return rule.probability
        return 0.0

    def should_fire(self, kind: str) -> bool:
        p = self.probability(kind)
        if p <= 0.0:
            return False
        if p >= 1.0:
            return True
        return self.rng.random() < p

    def enabled(self) -> bool:
        return any(r.probability > 0.0 for r in self.rules)


def _parse_rules(raw: str) -> list[ChaosRule]:
    rules: list[ChaosRule] = []
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        kind, _, prob_str = chunk.partition(":")
        try:
            prob = float(prob_str)
        except ValueError:
            continue
        if not 0.0 <= prob <= 1.0:
            continue
        rules.append(ChaosRule(kind=kind.strip(), probability=prob))
    return rules
