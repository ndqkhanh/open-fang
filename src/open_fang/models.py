"""OpenFang data model — briefs, DAGs, nodes, evidence, claims, reports."""
from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

NodeKind = Literal[
    "kb.lookup",
    "search.arxiv",
    "search.semantic_scholar",
    "search.github",
    "fetch.pdf",
    "parse.latex",
    "extract.claims",
    "verify.claim",
    "resolve.citation",
    "summarize.section",
    "compare.papers",
    "synthesize.briefing",
    "kb.promote",
    "permission.request",
    "reason",
    "hand-off",
]

NodeStatus = Literal["pending", "running", "parked", "done", "failed", "skipped"]


class Brief(BaseModel):
    """User research question."""

    question: str
    domain: str | None = None
    max_cost_usd: float = 0.50
    min_papers: int = 3
    require_peer_reviewed: bool = False
    target_length_words: int = 1500
    style: str = "standard"


class SourceRef(BaseModel):
    kind: str  # "arxiv" | "s2" | "github" | "kb" | "mock"
    identifier: str
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    published_at: str | None = None


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    source: SourceRef
    content: str
    span_start: int | None = None
    span_end: int | None = None
    channel: str = "body"  # "abstract" | "body" | "table" | "figure-caption"
    relevance: float = 1.0
    # v2.4: structured numeric/tabular values extracted from tables or prose.
    # Used by the ExecutableVerifier (Tier 4) as the `evidence` dict namespace.
    structured_data: dict[str, Any] = Field(default_factory=dict)
    # v7.4: delta-mode fields — when True the Evidence is a lightweight stub
    # referencing an existing KB paper via `delta_handle`. Content is empty;
    # resolve via sources.delta.resolve_delta(ev, kb).
    delta_mode: bool = False
    delta_handle: str | None = None


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    text: str
    evidence_ids: list[str]
    verified: bool = False
    verification_note: str = ""
    cross_channel_confirmed: bool = False
    # v2.4: Tier 2 warning when the LLM judge fails to distinguish the claim
    # from its fabricated mutants. Does not veto verification on its own.
    mutation_warning: bool = False
    # v2.4: Tier 4 result — True if the executable verifier's assertion passed.
    # False when it ran and failed; None when no script was provided.
    executable_passed: bool | None = None


class Section(BaseModel):
    title: str
    claims: list[Claim]


class Node(BaseModel):
    """A single DAG node in a research plan."""

    id: str
    kind: NodeKind
    args: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    status: NodeStatus = "pending"
    output: Any = None
    error: str | None = None
    risk: Literal["low", "medium", "high"] = "low"


class DAG(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    nodes: list[Node]
    estimated_cost_usd: float = 0.0


class Report(BaseModel):
    brief: Brief
    summary: str = ""
    sections: list[Section]
    references: list[SourceRef]
    techniques_extracted: list[str] = Field(default_factory=list)
    faithfulness_ratio: float = 1.0
    verified_claims: int = 0
    total_claims: int = 0
    cost_usd: float = 0.0
    dag_id: str = ""
    trace_id: str = ""

    def to_markdown(self) -> str:
        lines = [f"# {self.brief.question}", ""]
        if self.summary:
            lines.extend([self.summary, ""])
        citation_num: dict[str, int] = {}
        counter = 1
        for section in self.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            for claim in section.claims:
                nums: list[int] = []
                for eid in claim.evidence_ids:
                    if eid not in citation_num:
                        citation_num[eid] = counter
                        counter += 1
                    nums.append(citation_num[eid])
                cite_str = " " + ",".join(f"[{n}]" for n in nums) if nums else ""
                suffix = "" if claim.verified else " *(unverified)*"
                lines.append(f"- {claim.text}{cite_str}{suffix}")
            lines.append("")
        lines.append("## References")
        lines.append("")
        for ref in self.references:
            title = ref.title or ref.identifier
            lines.append(f"- [{title}]({ref.identifier})")
        lines.append("")
        lines.append(
            f"*faithfulness: {self.faithfulness_ratio:.0%}; "
            f"claims: {self.verified_claims}/{self.total_claims}; "
            f"cost: ${self.cost_usd:.2f}*"
        )
        return "\n".join(lines)


class Span(BaseModel):
    """Gnomon-shaped primitive span for observability."""

    trace_id: str
    node_id: str
    kind: NodeKind
    started_at: float
    ended_at: float
    inputs_preview: str = ""
    outputs_preview: str = ""
    cost_usd: float = 0.0
    verdict: Literal["ok", "error", "parked", "skipped"] = "ok"
    error: str | None = None
    # v4.4: sprint-lifecycle stage label (plan/retrieve/extract/verify/synthesize/critique/publish/reflect).
    stage: str | None = None
