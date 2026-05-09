from __future__ import annotations

from open_fang.models import Evidence, Node, SourceRef
from open_fang.sources.mock import MockSource
from open_fang.sources.router import SourceRouter
from open_fang.supervisor.specialist import (
    ClaimVerifierAgent,
    CriticAgent,
    DeepReadAgent,
    SpecialistContext,
    SurveyAgent,
    SynthesisAgent,
)


def _ctx(canned: list[Evidence] | None = None) -> SpecialistContext:
    source = MockSource(canned=canned) if canned is not None else MockSource()
    return SpecialistContext(source_router=SourceRouter(arxiv=source, fallback=source))


def _node(kind: str, **args) -> Node:
    return Node(id="n1", kind=kind, args=args)  # type: ignore[arg-type]


def test_survey_agent_handles_three_search_kinds():
    sa = SurveyAgent()
    assert sa.handles == {"search.arxiv", "search.semantic_scholar", "search.github"}


def test_survey_agent_executes_search():
    ev = [Evidence(source=SourceRef(kind="arxiv", identifier="x", title="x"), content="x")]
    outcome = SurveyAgent().execute(_node("search.arxiv", query="q"), _ctx(canned=ev))
    assert outcome == ev


def test_survey_agent_with_no_router_returns_empty():
    outcome = SurveyAgent().execute(_node("search.arxiv", query="q"), SpecialistContext())
    assert outcome == []


def test_deep_read_agent_claims_extraction_kinds():
    sa = DeepReadAgent()
    assert sa.handles == {"fetch.pdf", "parse.latex", "extract.claims"}
    assert sa.execute(_node("fetch.pdf"), _ctx()) == []


def test_claim_verifier_agent_claims_verify_claim():
    sa = ClaimVerifierAgent()
    assert "verify.claim" in sa.handles
    assert sa.execute(_node("verify.claim"), _ctx()) == []


def test_synthesis_agent_claims_three_kinds():
    sa = SynthesisAgent()
    assert sa.handles == {"synthesize.briefing", "summarize.section", "compare.papers"}


def test_critic_agent_claims_reason_and_handoff():
    sa = CriticAgent()
    assert sa.handles == {"reason", "hand-off"}
