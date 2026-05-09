"""50-brief evaluation corpus (v2.7 expansion from the original 20).

Each brief reuses evidence from the 5-paper fixture set (paper_data.FIXTURES);
variations span phrasing, style, length, and cross-paper questions. Designed
so the deterministic pipeline satisfies the per-brief rubric on every
canonical evidence set.
"""
from __future__ import annotations

from dataclasses import dataclass

from open_fang.models import Brief, Evidence

from .paper_data import FIXTURES


@dataclass(frozen=True)
class EvalBrief:
    brief: Brief
    evidence: list[Evidence]
    min_claims: int = 2
    min_faithfulness: float = 0.90
    tag: str = ""


def _with(
    question: str,
    fixture_idx: int,
    *,
    tag: str = "",
    style: str = "standard",
    length: int = 600,
) -> EvalBrief:
    fx = FIXTURES[fixture_idx]
    return EvalBrief(
        brief=Brief(question=question, style=style, target_length_words=length),
        evidence=fx["evidence"],
        tag=tag or f"fixture-{fixture_idx}",
    )


def _combined(
    question: str,
    fixture_ids: list[int],
    *,
    tag: str,
    style: str = "standard",
    length: int = 800,
) -> EvalBrief:
    """Combine evidence from multiple fixtures for cross-paper briefs."""
    evidence: list[Evidence] = []
    for idx in fixture_ids:
        evidence.extend(FIXTURES[idx]["evidence"])
    return EvalBrief(
        brief=Brief(question=question, style=style, target_length_words=length),
        evidence=evidence,
        tag=tag,
    )


BRIEFS: list[EvalBrief] = [
    # ----- Single-paper briefs — 4 per fixture × 5 fixtures = 20 (original) -----
    _with("What is ReWOO and how does it differ from ReAct?", 0, tag="rewoo-primary"),
    _with("Compare ReWOO's planner-executor split to ReAct's single-loop design.", 0, tag="rewoo-compare"),
    _with("ReWOO token-efficiency claim", 0, tag="rewoo-terse", style="terse", length=300),
    _with("Explain ReWOO's DAG of tool calls in detail", 0, tag="rewoo-long", style="exhaustive", length=1200),
    _with("What is Reflexion and how does it improve agent performance?", 1, tag="reflexion-primary"),
    _with("How does Reflexion use verbal lessons across episodes?", 1, tag="reflexion-verbal"),
    _with("Reflexion episodic memory", 1, tag="reflexion-memory", style="terse", length=300),
    _with("When is Reflexion most effective on downstream tasks?", 1, tag="reflexion-effectiveness"),
    _with("What is the Voyager skill library approach?", 2, tag="voyager-primary"),
    _with("How does Voyager verify new skills before adding them?", 2, tag="voyager-verify"),
    _with("Voyager lifelong learning", 2, tag="voyager-lifelong", style="terse", length=300),
    _with("How does Voyager retrieve skills during planning?", 2, tag="voyager-retrieve"),
    _with("What is Plan-and-Solve prompting?", 3, tag="pas-primary"),
    _with("Plan-and-Solve on arithmetic benchmarks", 3, tag="pas-arithmetic"),
    _with("Plan-and-Solve", 3, tag="pas-terse", style="terse", length=300),
    _with("Walk through Plan-and-Solve's two-step prompting strategy", 3, tag="pas-long"),
    _with("What is Tree of Thoughts and how does it explore reasoning paths?", 4, tag="tot-primary"),
    _with("How does LATS combine Tree of Thoughts with tool use?", 4, tag="lats"),
    _with("Tree of Thoughts tradeoffs", 4, tag="tot-tradeoff"),
    _with("Backtracking and lookahead in Tree of Thoughts", 4, tag="tot-search", style="standard"),
    # ----- v2.7 additions — 2 more per fixture × 5 = 10 deeper single-paper briefs -----
    _with("What problem does ReWOO solve?", 0, tag="rewoo-problem"),
    _with("Summarize ReWOO in one paragraph", 0, tag="rewoo-summary", length=400),
    _with("Reflexion vs standard fine-tuning: what's the trade-off?", 1, tag="reflexion-vs-sft"),
    _with("Summarize Reflexion in one paragraph", 1, tag="reflexion-summary", length=400),
    _with("Voyager: what makes skills durable across runs?", 2, tag="voyager-durable"),
    _with("Summarize Voyager in one paragraph", 2, tag="voyager-summary", length=400),
    _with("Plan-and-Solve: decomposition vs direct execution", 3, tag="pas-decomp"),
    _with("Summarize Plan-and-Solve", 3, tag="pas-summary", length=400),
    _with("Tree of Thoughts vs chain-of-thought: cost and benefit", 4, tag="tot-cost"),
    _with("Summarize Tree of Thoughts in one paragraph", 4, tag="tot-summary", length=400),
    # ----- v2.7 additions — 20 cross-paper briefs combining 2–3 fixtures each -----
    _combined(
        "Compare ReWOO's decoupled planning to Plan-and-Solve's step-by-step execution.",
        [0, 3], tag="rewoo-vs-pas",
    ),
    _combined(
        "How do ReWOO and Tree of Thoughts differ in their treatment of tool calls?",
        [0, 4], tag="rewoo-vs-tot",
    ),
    _combined(
        "How does Reflexion relate to Voyager's skill library?",
        [1, 2], tag="reflexion-vs-voyager",
    ),
    _combined(
        "Plan-and-Solve vs Tree of Thoughts: when is each appropriate?",
        [3, 4], tag="pas-vs-tot",
    ),
    _combined(
        "Trace the lineage from ReAct to Reflexion to Voyager.",
        [0, 1, 2], tag="react-reflexion-voyager-lineage",
        length=1000,
    ),
    _combined(
        "Compare the five reasoning-architecture families: ReWOO, Reflexion, Voyager, Plan-and-Solve, and Tree of Thoughts.",
        [0, 1, 2, 3, 4], tag="five-families-compare",
        length=1500, style="exhaustive",
    ),
    _combined(
        "Which of these approaches is most useful for long-horizon research tasks?",
        [0, 1, 2, 3, 4], tag="long-horizon-selection",
        length=800,
    ),
    _combined("ReWOO + Reflexion: could they be combined?", [0, 1], tag="rewoo-plus-reflexion"),
    _combined("Voyager + Plan-and-Solve: complementary or redundant?", [2, 3], tag="voyager-plus-pas"),
    _combined("Tree of Thoughts + Voyager: could a skill library benefit from ToT search?", [2, 4], tag="tot-plus-voyager"),
    _combined("ReWOO + Tree of Thoughts: DAG planning meets backtracking search", [0, 4], tag="rewoo-plus-tot"),
    _combined("Reflexion + Plan-and-Solve: verbal lessons in a structured plan", [1, 3], tag="reflexion-plus-pas"),
    _combined("Comparing memory mechanisms: Reflexion's episodic vs Voyager's skill library", [1, 2], tag="memory-mechanisms"),
    _combined("Comparing planning styles: ReWOO DAG vs Plan-and-Solve linear", [0, 3], tag="planning-styles"),
    _combined("Comparing search strategies: Tree of Thoughts vs Voyager's retrieval", [2, 4], tag="search-strategies"),
    _combined("Reflexion vs Plan-and-Solve: what do they share?", [1, 3], tag="reflexion-shared-pas"),
    _combined("Which paper explicitly addresses compute cost trade-offs?", [0, 2, 4], tag="compute-cost-focus"),
    _combined("Which paper targets embodied agents?", [1, 2], tag="embodied-focus"),
    _combined("ToT + ReWOO in a shared planner", [0, 4], tag="tot-rewoo-planner"),
    _combined(
        "Synthesize the common thread across all five approaches.",
        [0, 1, 2, 3, 4], tag="common-thread", length=1000,
    ),
]

assert len(BRIEFS) == 50, f"eval corpus must contain 50 briefs, got {len(BRIEFS)}"
