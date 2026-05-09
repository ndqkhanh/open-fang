"""OpenFangPipeline: Phase-1 planner + Phase-2 scheduler + post-synthesis verify + KB promote + HAFC attribution."""
from __future__ import annotations

from dataclasses import dataclass, field

from harness_core.observability import Tracer

from .attribution.classifier import AttributionReport, HAFCClassifier
from .kb.promote import PromotionReport, promote_report
from .kb.store import KBStore
from .memory.fang import FANGLoader
from .memory.store import MemoryStore
from .models import Brief, Report
from .observe.tracer import SpanRecorder
from .planner.llm_planner import DAGPlanner
from .scheduler.engine import SchedulerEngine
from .skills.registry import SkillRegistry
from .skills.schema import Skill
from .sources.mock import MockSource
from .synthesize.writer import SynthesisWriter
from .verify.claim_verifier import ClaimVerifier
from .verify.critic import CriticAgent


@dataclass
class PipelineResult:
    report: Report
    parked_nodes: list[str]
    failed_nodes: list[str]
    downgraded_claims: list[str]
    promotion: PromotionReport | None = None
    activated_skills: list[str] = field(default_factory=list)
    observation_ids: list[str] = field(default_factory=list)
    attribution: AttributionReport | None = None  # v6.0 HAFC-lite


class OpenFangPipeline:
    """Brief → DAG → scheduled execution → synthesized + verified + critiqued report."""

    def __init__(
        self,
        *,
        planner: DAGPlanner | None = None,
        scheduler: SchedulerEngine | None = None,
        synthesizer: SynthesisWriter | None = None,
        verifier: ClaimVerifier | None = None,
        critic: CriticAgent | None = None,
        kb: KBStore | None = None,
        memory: MemoryStore | None = None,
        fang: FANGLoader | None = None,
        skill_registry: SkillRegistry | None = None,
        tracer: Tracer | None = None,
        span_recorder: SpanRecorder | None = None,
    ) -> None:
        self.planner = planner or DAGPlanner()
        if scheduler is None:
            self.scheduler = SchedulerEngine(source=MockSource(), kb=kb)
        else:
            self.scheduler = scheduler
            if kb is not None and scheduler.kb is None:
                scheduler.kb = kb
        self.kb = kb if kb is not None else self.scheduler.kb
        self.memory = memory
        self.synthesizer = synthesizer or SynthesisWriter()
        self.verifier = verifier or ClaimVerifier()
        self.critic = critic or CriticAgent()
        self.fang = fang or FANGLoader()
        self.skill_registry = skill_registry
        self.tracer = tracer or Tracer()
        self.span_recorder = span_recorder or SpanRecorder()

    def run(self, brief: Brief) -> PipelineResult:
        with self.tracer.span("openfang.pipeline", question_preview=brief.question[:80]):
            persona = self.fang.load()
            activated: list[Skill] = []
            if self.skill_registry is not None:
                activated = self.skill_registry.activate(brief.question, max_results=3)
            with self.tracer.span("openfang.plan", skills_activated=len(activated)):
                dag = self.planner.plan(brief, persona=persona)
            with self.tracer.span("openfang.schedule", nodes=len(dag.nodes)):
                evidence, parked, failed = self.scheduler.run(dag, recorder=self.span_recorder)
            with self.tracer.span("openfang.synthesize", evidence=len(evidence)):
                report = self.synthesizer.write(brief, evidence)
            with self.tracer.span("openfang.verify"):
                self.verifier.verify(report, evidence)
            with self.tracer.span("openfang.critique"):
                critique = self.critic.critique(report, evidence)
            promotion: PromotionReport | None = None
            if self.kb is not None:
                with self.tracer.span("openfang.kb.promote"):
                    promotion = promote_report(report, evidence, self.kb)
            observation_ids: list[str] = []
            if self.memory is not None and self.span_recorder.spans:
                for span in self.span_recorder.spans:
                    observation_ids.append(self.memory.append(span))
            report.dag_id = dag.id
            report.cost_usd = round(dag.estimated_cost_usd, 2)
        result = PipelineResult(
            report=report,
            parked_nodes=parked,
            failed_nodes=failed,
            downgraded_claims=critique.downgraded,
            promotion=promotion,
            activated_skills=[s.name for s in activated],
            observation_ids=observation_ids,
        )
        # v6.0 HAFC-lite: run attribution when the result has any failure signal.
        if (
            report.faithfulness_ratio < 0.9
            or result.failed_nodes
            or result.parked_nodes
            or result.downgraded_claims
        ):
            result.attribution = HAFCClassifier().classify(result)
        return result
