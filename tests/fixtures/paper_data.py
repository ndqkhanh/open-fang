"""Five-paper fixture set for Phase-3 faithfulness evaluation.

Each fixture is a plausible AI/agent paper with enough evidence content that the
SynthesisWriter + ClaimVerifier (lexical + optional LLM judge) can confidently
verify ≥90% of auto-generated claims. Used by tests/evaluation/test_five_paper_faithfulness.py.
"""
from __future__ import annotations

from open_fang.models import Brief, Evidence, SourceRef


def _ev(
    eid: str,
    kind: str,
    identifier: str,
    title: str,
    authors: list[str],
    content: str,
    *,
    channel: str = "abstract",
) -> Evidence:
    return Evidence(
        id=eid,
        source=SourceRef(
            kind=kind,
            identifier=identifier,
            title=title,
            authors=authors,
            published_at="2023",
        ),
        content=content,
        channel=channel,
    )


FIXTURES: list[dict] = [
    {
        "brief": Brief(
            question="What is ReWOO and how does it differ from ReAct?",
            target_length_words=600,
        ),
        "evidence": [
            _ev(
                "rewoo-1", "arxiv", "arxiv:2305.18323",
                "ReWOO: Decoupling Reasoning from Observations",
                ["Binfeng Xu"],
                "ReWOO decouples reasoning from observations. The planner emits a DAG "
                "of tool calls resolved in parallel.",
            ),
            _ev(
                "rewoo-2", "arxiv", "arxiv:2305.18323",
                "ReWOO: Decoupling Reasoning from Observations",
                ["Binfeng Xu"],
                "ReWOO reduces token usage fivefold relative to ReAct on multi-hop tasks.",
                channel="body",
            ),
            _ev(
                "react-1", "arxiv", "arxiv:2210.03629",
                "ReAct: Synergizing Reasoning and Acting",
                ["Shunyu Yao"],
                "ReAct interleaves reasoning and acting within a single loop of thought-action-observation turns.",
            ),
        ],
    },
    {
        "brief": Brief(
            question="What is Reflexion and how does it improve agent performance?",
            target_length_words=500,
        ),
        "evidence": [
            _ev(
                "refl-1", "arxiv", "arxiv:2303.11366",
                "Reflexion: Language Agents with Verbal Reinforcement Learning",
                ["Noah Shinn"],
                "Reflexion extracts verbal lessons after each episode and appends them to the agent system prompt.",
            ),
            _ev(
                "refl-2", "arxiv", "arxiv:2303.11366",
                "Reflexion",
                ["Noah Shinn"],
                "Reflexion improves downstream task success when objective feedback signals are available.",
                channel="body",
            ),
            _ev(
                "refl-3", "arxiv", "arxiv:2303.11366",
                "Reflexion",
                ["Noah Shinn"],
                "Reflexion maintains an episodic memory of past failures to avoid repeating similar mistakes.",
                channel="body",
            ),
        ],
    },
    {
        "brief": Brief(
            question="What is the Voyager skill library approach?",
            target_length_words=500,
        ),
        "evidence": [
            _ev(
                "voy-1", "arxiv", "arxiv:2305.16291",
                "Voyager: An Open-Ended Embodied Agent",
                ["Guanzhi Wang"],
                "Voyager proposes a lifelong skill library that accumulates reusable programs across tasks.",
            ),
            _ev(
                "voy-2", "arxiv", "arxiv:2305.16291",
                "Voyager",
                ["Guanzhi Wang"],
                "Voyager retrieves relevant skills from the library before planning new actions.",
                channel="body",
            ),
            _ev(
                "voy-3", "arxiv", "arxiv:2305.16291",
                "Voyager",
                ["Guanzhi Wang"],
                "Voyager verifies each new skill via execution before committing it to the library.",
                channel="body",
            ),
        ],
    },
    {
        "brief": Brief(
            question="Plan-and-Solve prompting",
            target_length_words=400,
        ),
        "evidence": [
            _ev(
                "plan-1", "arxiv", "arxiv:2305.04091",
                "Plan-and-Solve Prompting",
                ["Lei Wang"],
                "Plan-and-Solve prompts the model to first devise a plan and then execute each step sequentially.",
            ),
            _ev(
                "plan-2", "arxiv", "arxiv:2305.04091",
                "Plan-and-Solve",
                ["Lei Wang"],
                "Plan-and-Solve outperforms zero-shot CoT on arithmetic benchmarks.",
                channel="body",
            ),
        ],
    },
    {
        "brief": Brief(
            question="Tree of Thoughts / LATS search over reasoning paths",
            target_length_words=500,
        ),
        "evidence": [
            _ev(
                "tot-1", "arxiv", "arxiv:2305.10601",
                "Tree of Thoughts",
                ["Shunyu Yao"],
                "Tree of Thoughts explores multiple reasoning paths with backtracking and lookahead.",
            ),
            _ev(
                "tot-2", "arxiv", "arxiv:2310.04406",
                "LATS: Language Agent Tree Search",
                ["Andy Zhou"],
                "LATS combines Tree of Thoughts search with agent tool use in a unified framework.",
                channel="body",
            ),
            _ev(
                "tot-3", "arxiv", "arxiv:2305.10601",
                "Tree of Thoughts",
                ["Shunyu Yao"],
                "Tree of Thoughts increases solution accuracy on hard problems at higher compute cost.",
                channel="body",
            ),
        ],
    },
]
