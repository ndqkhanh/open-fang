"""Chaos × HAFC scanner (v6.4).

Invokes the pipeline N times against a fixed brief under varying chaos
configurations, then groups the resulting attribution reports to build a
fragility matrix: which primitive degrades under which perturbation?

v6.4 ships the scanner. v7 ships the response (auto-generated hardening patches).
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field

from .attribution.primitives import Primitive
from .models import Brief
from .pipeline import OpenFangPipeline
from .scheduler.chaos import ChaosInjector, ChaosRule
from .scheduler.engine import SchedulerEngine


@dataclass
class FragilityMatrixEntry:
    chaos_mode: str
    probability: float
    primitive_counts: dict[Primitive, int] = field(default_factory=dict)
    total_runs: int = 0
    total_attributions: int = 0

    def top_primitive(self) -> tuple[Primitive, int] | None:
        if not self.primitive_counts:
            return None
        primitive = max(self.primitive_counts, key=lambda p: self.primitive_counts[p])
        return primitive, self.primitive_counts[primitive]


@dataclass
class FragilityMatrix:
    entries: list[FragilityMatrixEntry] = field(default_factory=list)

    def to_rows(self) -> list[dict]:
        return [
            {
                "chaos_mode": e.chaos_mode,
                "probability": e.probability,
                "total_runs": e.total_runs,
                "total_attributions": e.total_attributions,
                "primitive_counts": {p.value: c for p, c in e.primitive_counts.items()},
            }
            for e in self.entries
        ]


class ChaosScanner:
    def __init__(self, *, pipeline_factory) -> None:
        """`pipeline_factory` is a callable taking (ChaosInjector | None) → OpenFangPipeline."""
        self.pipeline_factory = pipeline_factory

    def scan(
        self,
        brief: Brief,
        *,
        configs: list[tuple[str, float]],
        rounds: int = 5,
        seed: int = 0,
    ) -> FragilityMatrix:
        matrix = FragilityMatrix()
        for config_idx, (kind, probability) in enumerate(configs):
            entry = FragilityMatrixEntry(chaos_mode=kind, probability=probability)
            counts: Counter[Primitive] = Counter()
            for round_idx in range(rounds):
                # Deterministic per (config, round) seed.
                rng = random.Random(seed * 1000 + config_idx * rounds + round_idx)
                injector = ChaosInjector(
                    rules=[ChaosRule(kind=kind, probability=probability)],
                    rng=rng,
                )
                pipeline = self.pipeline_factory(injector)
                result = pipeline.run(brief)
                entry.total_runs += 1
                if result.attribution is None:
                    continue
                for r in result.attribution.results:
                    counts[r.primitive] += 1
                    entry.total_attributions += 1
            entry.primitive_counts = dict(counts)
            matrix.entries.append(entry)
        return matrix


def make_default_pipeline_factory(source=None, kb=None):
    """Build a minimal pipeline factory for scanner use."""

    def factory(injector: ChaosInjector | None) -> OpenFangPipeline:
        scheduler = SchedulerEngine(
            source=source,
            kb=kb,
            chaos=injector or ChaosInjector(),
        )
        return OpenFangPipeline(scheduler=scheduler, kb=kb)

    return factory
