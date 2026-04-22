"""v3.1 exit criterion: ≥5× token reduction vs raw-transcript baseline on 10 turns.

The baseline is the naive transcript (every turn + every tool-use rendered
verbatim). The progressive stack is persona + Tier A compact index + last-2
buffer turns. Both are measured with the same token approximation to avoid
apples-to-oranges comparison.
"""
from __future__ import annotations

from pathlib import Path

from open_fang.kb.store import KBStore
from open_fang.memory.fang import FANGLoader
from open_fang.memory.progressive import ProgressiveContextAssembler
from open_fang.memory.store import MemoryStore
from open_fang.memory.working import WorkingBuffer
from open_fang.models import Span

TURNS = 10
TOOL_USES_PER_TURN = 5
REDUCTION_FLOOR = 5.0

# A plausibly-chunky turn (user prompt + long assistant response + tool-use output).
_RAW_TURN = (
    "user: Please research ReWOO in depth and compare to every paper in the KB. "
    "Include a full citation graph and synthesize a briefing.\n\n"
    "assistant: [long response of about 600 characters explaining ReWOO's "
    "decoupling of reasoning from observations, the DAG planner, the parallel "
    "tool-call resolution, the 5x token reduction claim, the comparison to "
    "ReAct's single-loop design, the fault-locality advantages at node granularity, "
    "and the scheduling implications for long-horizon tasks that benefit from "
    "deterministic orchestration over free-form reactive loops...]\n\n"
    "tool_use: search.arxiv(query='rewoo'); results: [...long list of papers with "
    "abstracts and metadata spanning many hundreds of characters...]\n\n"
    "tool_use: kb.lookup(query='rewoo'); results: [...more chunky evidence...]\n\n"
)


def _span(i: int, kind: str = "search.arxiv") -> Span:
    return Span(
        trace_id=f"t{i}",
        node_id=f"n{i}",
        kind=kind,  # type: ignore[arg-type]
        started_at=float(i),
        ended_at=float(i) + 0.1,
        verdict="ok",  # type: ignore[arg-type]
    )


def _raw_transcript(n_turns: int) -> str:
    return "".join(_RAW_TURN for _ in range(n_turns))


def test_progressive_context_is_at_least_5x_smaller(tmp_path: Path):
    # Progressive stack.
    fang_path = tmp_path / "FANG.md"
    fang_path.write_text(
        "# FANG\n\nDomain: AI agents. Evidence bar: arxiv OK.",
        encoding="utf-8",
    )
    kb = KBStore(db_path=":memory:").open()
    memory = MemoryStore(kb)
    for i in range(TURNS * TOOL_USES_PER_TURN):
        memory.append(_span(i))

    buffer = WorkingBuffer(max_turns=2)
    for i in range(TURNS):
        buffer.add("user", f"turn {i}")
        buffer.add("assistant", f"reply {i}")

    assembler = ProgressiveContextAssembler(
        fang=FANGLoader(path=fang_path),
        buffer=buffer,
        memory=memory,
        compact_limit=20,
    )
    progressive_text = assembler.assemble()
    progressive_tokens = ProgressiveContextAssembler.token_approx(progressive_text)

    # Raw transcript baseline.
    raw_text = _raw_transcript(TURNS)
    raw_tokens = ProgressiveContextAssembler.token_approx(raw_text)

    ratio = raw_tokens / max(1, progressive_tokens)
    assert ratio >= REDUCTION_FLOOR, (
        f"progressive={progressive_tokens} tokens, raw={raw_tokens} tokens, "
        f"ratio={ratio:.2f} < {REDUCTION_FLOOR}"
    )


def test_persona_survives_progressive_compaction(tmp_path: Path):
    """Persona lines must appear verbatim even when memory + buffer are saturated."""
    fang_path = tmp_path / "FANG.md"
    persona_lines = [
        "Domain: AI agents.",
        "Citation style: APA-inline + arxiv id.",
        "Preferred venues: NeurIPS, ICML, ICLR.",
    ]
    fang_path.write_text("# FANG\n\n" + "\n".join(persona_lines), encoding="utf-8")

    kb = KBStore(db_path=":memory:").open()
    memory = MemoryStore(kb)
    for i in range(100):
        memory.append(_span(i))

    buffer = WorkingBuffer(max_turns=2)
    for i in range(20):
        buffer.add("user", f"turn {i}")

    assembler = ProgressiveContextAssembler(
        fang=FANGLoader(path=fang_path),
        buffer=buffer,
        memory=memory,
    )
    ctx = assembler.assemble()
    for line in persona_lines:
        assert line in ctx, f"persona line missing after compaction: {line!r}"
