"""Supervisor: dispatch by node kind + per-specialist stats + crash isolation."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Node
from .specialist import (
    ClaimVerifierAgent,
    CriticAgent,
    DeepReadAgent,
    MethodologistAgent,
    PublisherAgent,
    ResearchDirectorAgent,
    Specialist,
    SpecialistContext,
    SpecialistOutcome,
    SurveyAgent,
    SynthesisAgent,
    ThreatModelerAgent,
)


@dataclass
class SpecialistStat:
    dispatched: int = 0
    errors: int = 0


@dataclass
class SupervisorStats:
    per_specialist: dict[str, SpecialistStat] = field(default_factory=dict)

    def record(self, specialist_name: str, *, error: bool = False) -> None:
        stat = self.per_specialist.setdefault(specialist_name, SpecialistStat())
        stat.dispatched += 1
        if error:
            stat.errors += 1


class Supervisor:
    def __init__(self, specialists: list[Specialist]) -> None:
        self.specialists = specialists
        self._by_kind: dict[str, Specialist] = {}
        for sp in specialists:
            for kind in sp.handles:
                self._by_kind[kind] = sp
        self.stats = SupervisorStats()

    def dispatch(self, node: Node, context: SpecialistContext) -> SpecialistOutcome:
        specialist = self._by_kind.get(node.kind)
        if specialist is None:
            return SpecialistOutcome(specialist=None, handled=False)
        try:
            output = specialist.execute(node, context)
            self.stats.record(specialist.name)
            return SpecialistOutcome(
                specialist=specialist.name,
                output=output,
                handled=True,
            )
        except Exception as exc:  # noqa: BLE001 — crash isolation
            self.stats.record(specialist.name, error=True)
            return SpecialistOutcome(
                specialist=specialist.name,
                handled=True,
                error=f"{type(exc).__name__}: {exc}",
            )

    def roster(self) -> list[dict]:
        """Machine-readable roster for the status endpoint."""
        return [
            {
                "name": sp.name,
                "stage": sp.stage,
                "handles": sorted(sp.handles),
            }
            for sp in self.specialists
        ]


def default_supervisor() -> Supervisor:
    """Return a supervisor wired with the v4.0 9-specialist cohort."""
    return Supervisor(
        specialists=[
            ResearchDirectorAgent(),
            SurveyAgent(),
            DeepReadAgent(),
            ClaimVerifierAgent(),
            MethodologistAgent(),
            SynthesisAgent(),
            CriticAgent(),
            ThreatModelerAgent(),
            PublisherAgent(),
        ]
    )
