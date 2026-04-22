"""Specialist base class + 9-role cohort (v4.0).

v3.2 shipped 5 specialists. v4.0 adds ResearchDirector, Methodologist,
ThreatModeler, Publisher to complete the sprint lifecycle:
  plan → retrieve → extract → verify → synthesize → critique → threat-model
  → publish → reflect

Each specialist declares:
  - name (snake-case)
  - stage (one of the 9 lifecycle stages)
  - handles (set of NodeKind strings)
  - owned_skills (names of skills in skills/ this specialist activates)
  - verifier_tiers (which tiers run on its outputs)
  - model_family_preference ("anthropic" | "openai" | "either")
  - cost_ceiling_usd (per-invocation budget; 0.0 = no limit)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..kb.store import KBStore
from ..models import Evidence, Node
from ..sources.router import SourceRouter


@dataclass
class SpecialistContext:
    source_router: SourceRouter | None = None
    kb: KBStore | None = None
    evidence: list[Evidence] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class SpecialistOutcome:
    specialist: str | None
    output: Any = None
    handled: bool = False
    error: str | None = None


class Specialist(ABC):
    """One role-scoped unit of execution."""

    name: str = ""
    stage: str = ""
    handles: set[str] = set()
    owned_skills: tuple[str, ...] = ()
    verifier_tiers: tuple[str, ...] = ("lexical", "llm_judge")
    model_family_preference: str = "either"  # "anthropic" | "openai" | "either"
    cost_ceiling_usd: float = 0.0  # 0.0 = no cap

    @abstractmethod
    def execute(self, node: Node, context: SpecialistContext) -> Any: ...

    @classmethod
    def spec(cls) -> dict:
        """Return the SPECIALIST.md-shaped declaration as a dict."""
        return {
            "name": cls.name,
            "stage": cls.stage,
            "handles": sorted(cls.handles),
            "owned_skills": list(cls.owned_skills),
            "verifier_tiers": list(cls.verifier_tiers),
            "model_family_preference": cls.model_family_preference,
            "cost_ceiling_usd": cls.cost_ceiling_usd,
        }


# -----------------------------------------------------------------------------
# v3.2 specialists — unchanged
# -----------------------------------------------------------------------------


class SurveyAgent(Specialist):
    name = "survey"
    stage = "retrieve"
    handles = {"search.arxiv", "search.semantic_scholar", "search.github"}
    owned_skills = ("citation-extraction",)
    verifier_tiers = ("lexical",)
    model_family_preference = "either"

    def execute(self, node: Node, context: SpecialistContext) -> list[Evidence]:
        if context.source_router is None:
            return []
        query = str(node.args.get("query", ""))
        max_results = int(node.args.get("max_results", 5))
        return context.source_router.search(node.kind, query, max_results=max_results)


class DeepReadAgent(Specialist):
    name = "deep-read"
    stage = "extract"
    handles = {"fetch.pdf", "parse.latex", "extract.claims"}
    owned_skills = ("claim-localization",)
    verifier_tiers = ("lexical", "llm_judge")

    def execute(self, node: Node, context: SpecialistContext) -> list[Evidence]:
        return []


class ClaimVerifierAgent(Specialist):
    name = "claim-verifier"
    stage = "verify"
    handles = {"verify.claim"}
    owned_skills = ("counter-example-generation", "reproduction-script")
    verifier_tiers = ("lexical", "mutation", "llm_judge", "executable", "critic")
    model_family_preference = "anthropic"

    def execute(self, node: Node, context: SpecialistContext) -> list[Evidence]:
        return []


class SynthesisAgent(Specialist):
    name = "synthesis"
    stage = "synthesize"
    handles = {"synthesize.briefing", "summarize.section", "compare.papers"}
    owned_skills = ()
    verifier_tiers = ("lexical", "llm_judge")
    model_family_preference = "anthropic"

    def execute(self, node: Node, context: SpecialistContext) -> list[Evidence]:
        return []


class CriticAgent(Specialist):
    name = "critic"
    stage = "critique"
    handles = {"reason", "hand-off"}
    owned_skills = ("peer-review",)
    verifier_tiers = ("critic",)
    model_family_preference = "openai"  # second opinion from a different family

    def execute(self, node: Node, context: SpecialistContext) -> list[Evidence]:
        return []


# -----------------------------------------------------------------------------
# v4.0 — new specialists
# -----------------------------------------------------------------------------


class ResearchDirectorAgent(Specialist):
    """Orchestration role — decomposes briefs, activates cohort, sets budget."""

    name = "research-director"
    stage = "plan"
    handles = set()  # v4.1 will extend NodeKind with `plan.orchestrate`
    owned_skills = ()
    verifier_tiers = ("lexical",)
    model_family_preference = "anthropic"
    cost_ceiling_usd = 0.05

    def execute(self, node: Node, context: SpecialistContext) -> list[Evidence]:
        return []


class MethodologistAgent(Specialist):
    """Methodology-verification role — checks experimental setups, reproducibility."""

    name = "methodologist"
    stage = "verify"
    handles = set()  # activated when claim-kind classifier tags "methodological"
    owned_skills = ("reproduction-script",)
    verifier_tiers = ("lexical", "llm_judge", "executable")
    model_family_preference = "either"

    def execute(self, node: Node, context: SpecialistContext) -> list[Evidence]:
        return []


class ThreatModelerAgent(Specialist):
    """Safety-critique role — flags dual-use concerns, prompt-injection surfaces."""

    name = "threat-modeler"
    stage = "critique"
    handles = set()
    owned_skills = ()
    verifier_tiers = ("critic",)
    model_family_preference = "anthropic"

    def execute(self, node: Node, context: SpecialistContext) -> list[Evidence]:
        return []


class PublisherAgent(Specialist):
    """Publish role — finalizes report format, adds citations, gates on faithfulness."""

    name = "publisher"
    stage = "publish"
    handles = set()  # activated at pipeline end, not as a DAG node
    owned_skills = ()
    verifier_tiers = ("lexical",)
    cost_ceiling_usd = 0.02

    def execute(self, node: Node, context: SpecialistContext) -> list[Evidence]:
        return []
