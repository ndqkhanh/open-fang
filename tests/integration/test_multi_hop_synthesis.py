"""v2.2 exit criterion (v2-plan.md §8): 10 synthesized briefs pass the verifier."""
from __future__ import annotations

import random

from open_fang.eval.synthesize import MultiHopBriefSynthesizer
from open_fang.kb.store import KBStore
from open_fang.models import SourceRef
from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.sources.mock import MockSource


def _seed_kb() -> KBStore:
    """Seed a small but well-connected KB from the 5-paper fixture set."""
    kb = KBStore(db_path=":memory:").open()
    papers = [
        ("arxiv:2305.18323", "ReWOO: Decoupling Reasoning from Observations",
         "ReWOO decouples reasoning from observations using a planner that "
         "emits a DAG of tool calls resolved in parallel."),
        ("arxiv:2210.03629", "ReAct: Synergizing Reasoning and Acting",
         "ReAct interleaves reasoning and acting in a single loop."),
        ("arxiv:2303.11366", "Reflexion: Language Agents with Verbal RL",
         "Reflexion extracts verbal lessons after each episode."),
        ("arxiv:2305.16291", "Voyager: An Open-Ended Embodied Agent",
         "Voyager proposes a lifelong skill library that accumulates reusable programs."),
        ("arxiv:2305.04091", "Plan-and-Solve Prompting",
         "Plan-and-Solve devises a plan first and then executes each step."),
        ("arxiv:2305.10601", "Tree of Thoughts",
         "Tree of Thoughts explores multiple reasoning paths with backtracking."),
        ("arxiv:2310.04406", "LATS: Language Agent Tree Search",
         "LATS combines Tree of Thoughts search with agent tool use."),
        ("arxiv:2308.08155", "AutoGen: Conversable Multi-Agent Framework",
         "AutoGen frames agents as conversable entities coordinating via messages."),
        ("arxiv:2307.07924", "MetaGPT: Meta Programming for Multi-Agent",
         "MetaGPT encodes SOPs into an assembly line of role agents."),
    ]
    for aid, title, abstract in papers:
        kb.upsert_paper(
            SourceRef(kind="arxiv", identifier=aid, title=title, authors=["X"]),
            abstract=abstract,
        )
    # Hand-author a richly connected citation graph for deterministic walks.
    edges = [
        ("arxiv:2305.18323", "arxiv:2210.03629", "extends"),    # ReWOO extends ReAct
        ("arxiv:2303.11366", "arxiv:2210.03629", "extends"),    # Reflexion extends ReAct
        ("arxiv:2305.16291", "arxiv:2210.03629", "cites"),      # Voyager cites ReAct
        ("arxiv:2305.16291", "arxiv:2303.11366", "cites"),      # Voyager cites Reflexion
        ("arxiv:2305.04091", "arxiv:2210.03629", "cites"),      # Plan-and-Solve cites ReAct
        ("arxiv:2305.10601", "arxiv:2305.18323", "cites"),      # ToT cites ReWOO
        ("arxiv:2305.10601", "arxiv:2210.03629", "cites"),      # ToT cites ReAct
        ("arxiv:2210.03629", "arxiv:2303.11366", "shares-author"),
        ("arxiv:2310.04406", "arxiv:2305.10601", "extends"),    # LATS extends ToT
        ("arxiv:2310.04406", "arxiv:2210.03629", "cites"),      # LATS cites ReAct
        ("arxiv:2308.08155", "arxiv:2210.03629", "cites"),      # AutoGen cites ReAct
        ("arxiv:2308.08155", "arxiv:2307.07924", "same-technique-family"),
        ("arxiv:2307.07924", "arxiv:2210.03629", "cites"),      # MetaGPT cites ReAct
        ("arxiv:2305.18323", "arxiv:2305.04091", "same-technique-family"),  # both "plan first"
    ]
    for src, dst, kind in edges:
        kb.add_edge(src, dst, kind)
    return kb


def test_synthesizes_ten_distinct_multi_hop_briefs():
    kb = _seed_kb()
    briefs = MultiHopBriefSynthesizer(kb).synthesize(n=10, hops=2, rng=random.Random(42))
    assert len(briefs) == 10
    signatures = {tuple(s.paper_id for s in b.walk) for b in briefs}
    # Each brief should cover a distinct walk signature.
    assert len(signatures) == 10
    # Every brief has at least 2 evidence items (the walk seed plus ≥1 hop).
    for sb in briefs:
        assert len(sb.evidence) >= 2
        assert sb.brief.question
        assert "Compare and connect" in sb.brief.question


def test_each_synthesized_brief_verifies():
    """Exit criterion: all 10 synthesized briefs pass the pipeline verifier."""
    kb = _seed_kb()
    briefs = MultiHopBriefSynthesizer(kb).synthesize(n=10, hops=2, rng=random.Random(42))
    assert len(briefs) == 10

    results = []
    for sb in briefs:
        pipeline = OpenFangPipeline(
            scheduler=SchedulerEngine(source=MockSource(canned=sb.evidence)),
        )
        results.append(pipeline.run(sb.brief))

    # Every brief must have produced at least one verified claim AND hit the
    # per-brief faithfulness floor (v2-plan.md §6 SLO).
    for i, r in enumerate(results):
        assert r.report.total_claims >= 1, f"brief {i}: no claims produced"
        assert r.report.verified_claims >= 1, f"brief {i}: no claims verified"
        assert r.report.faithfulness_ratio >= 0.90, (
            f"brief {i}: faithfulness {r.report.faithfulness_ratio:.2f} < 0.90"
        )

    # Aggregate: the mean faithfulness across 10 synthesized briefs is ≥ 0.90.
    avg = sum(r.report.faithfulness_ratio for r in results) / len(results)
    assert avg >= 0.90


def test_synthesizer_is_empty_on_isolated_kb():
    """KB with papers but no edges yields no multi-hop walks."""
    kb = KBStore(db_path=":memory:").open()
    for aid in ["a", "b", "c"]:
        kb.upsert_paper(
            SourceRef(kind="arxiv", identifier=f"arxiv:{aid}", title=aid), abstract=aid
        )
    assert MultiHopBriefSynthesizer(kb).synthesize(n=5) == []
