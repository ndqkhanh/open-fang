"""LLM-driven DAG planner.

The planner asks the LLM for a typed research DAG as JSON. On empty/invalid
output or when no LLM is wired, falls back to a deterministic canonical DAG
so the pipeline is always runnable.

LLM JSON contract:
    {
      "nodes": [
        {"id": "R1", "kind": "kb.lookup", "args": {"query": "..."},
         "depends_on": [], "risk": "low"},
        ...
      ],
      "estimated_cost_usd": 0.12
    }
"""
from __future__ import annotations

import json

from harness_core.messages import Message
from harness_core.models import LLMProvider, MockLLM

from ..models import DAG, Brief, Node, NodeKind
from .schema import DAGSchemaError, validate_dag

_SYSTEM_PROMPT = """You are OpenFang's research planner.
Given a research brief, emit a DAG of typed research nodes as strict JSON.

Allowed node kinds: kb.lookup, search.arxiv, search.semantic_scholar,
search.github, fetch.pdf, parse.latex, extract.claims, verify.claim,
resolve.citation, summarize.section, compare.papers, synthesize.briefing,
kb.promote, permission.request, reason, hand-off.

Return ONLY the JSON object with top-level keys `nodes` and `estimated_cost_usd`.
Every node has: id (str), kind (enum above), args (obj), depends_on (list[str]),
risk ("low" | "medium" | "high"). No explanation."""


_ALLOWED_KINDS: set[str] = {
    "kb.lookup", "search.arxiv", "search.semantic_scholar", "search.github",
    "fetch.pdf", "parse.latex", "extract.claims", "verify.claim",
    "resolve.citation", "summarize.section", "compare.papers",
    "synthesize.briefing", "kb.promote", "permission.request",
    "reason", "hand-off",
}


class DAGPlanner:
    """Research DAG planner.

    If `llm` is provided, the planner queries it for a JSON DAG; if parsing or
    schema validation fails, it falls back to the deterministic canonical DAG.
    If `llm` is None, always returns the canonical DAG (Phase-0 behavior).
    """

    def __init__(self, *, llm: LLMProvider | None = None) -> None:
        self.llm = llm

    def plan(self, brief: Brief, *, persona: str | None = None) -> DAG:
        if not brief.question.strip():
            raise ValueError("empty question")

        if self.llm is not None:
            dag = self._plan_via_llm(brief, persona=persona)
            if dag is not None:
                return dag
        return self._canonical_dag(brief)

    def _plan_via_llm(self, brief: Brief, *, persona: str | None) -> DAG | None:
        assert self.llm is not None
        prompt = self._user_prompt(brief, persona)
        reply = self.llm.generate(
            messages=[
                Message.system(_SYSTEM_PROMPT),
                Message.user(prompt),
            ],
            max_tokens=1500,
            temperature=0.0,
        )
        text = (reply.content or "").strip()
        if not text:
            return None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        try:
            dag = _dag_from_json(data, default_cost=0.05 * 6)
            validate_dag(dag)
            return dag
        except (DAGSchemaError, ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def _user_prompt(brief: Brief, persona: str | None) -> str:
        parts = [f"Research question: {brief.question}"]
        if brief.domain:
            parts.append(f"Domain: {brief.domain}")
        if persona:
            parts.append("Persona (FANG.md excerpts):")
            parts.append(persona[:1000])
        parts.append(f"Target length: {brief.target_length_words} words")
        parts.append(f"Cost ceiling: ${brief.max_cost_usd:.2f}")
        parts.append("Emit the JSON DAG now.")
        return "\n".join(parts)

    @staticmethod
    def _canonical_dag(brief: Brief) -> DAG:
        query = brief.question
        nodes: list[Node] = [
            Node(id="R1", kind="kb.lookup", args={"query": query}),
            Node(id="R2", kind="search.arxiv", args={"query": query, "max_results": 5}),
            Node(
                id="R3",
                kind="fetch.pdf",
                args={"from": "R2", "top_k": 3},
                depends_on=["R2"],
            ),
            Node(
                id="R4",
                kind="extract.claims",
                args={"from": "R3"},
                depends_on=["R3"],
            ),
            Node(
                id="R5",
                kind="verify.claim",
                args={"from": "R4"},
                depends_on=["R4"],
            ),
            Node(
                id="R6",
                kind="synthesize.briefing",
                args={"from": "R5", "target_length_words": brief.target_length_words},
                depends_on=["R1", "R5"],
            ),
        ]
        dag = DAG(nodes=nodes, estimated_cost_usd=0.05 * len(nodes))
        validate_dag(dag)
        return dag


def _dag_from_json(data: dict, *, default_cost: float) -> DAG:
    raw_nodes = data.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ValueError("nodes must be a non-empty list")

    nodes: list[Node] = []
    for raw in raw_nodes:
        if not isinstance(raw, dict):
            raise TypeError("node must be an object")
        kind = raw.get("kind")
        if kind not in _ALLOWED_KINDS:
            raise ValueError(f"unknown node kind: {kind!r}")
        nodes.append(
            Node(
                id=str(raw["id"]),
                kind=kind,  # type: ignore[arg-type]
                args=dict(raw.get("args", {})),
                depends_on=list(raw.get("depends_on", [])),
                risk=raw.get("risk", "low"),  # type: ignore[arg-type]
            )
        )
    cost = float(data.get("estimated_cost_usd", default_cost))
    return DAG(nodes=nodes, estimated_cost_usd=cost)


def mock_planner() -> DAGPlanner:
    """Convenience factory used in tests."""
    return DAGPlanner(llm=MockLLM())


__all__ = ["DAGPlanner", "NodeKind", "mock_planner"]
