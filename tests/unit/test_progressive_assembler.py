from __future__ import annotations

from pathlib import Path

from open_fang.kb.store import KBStore
from open_fang.memory.fang import FANGLoader
from open_fang.memory.progressive import ProgressiveContextAssembler
from open_fang.memory.store import MemoryStore
from open_fang.memory.working import WorkingBuffer
from open_fang.models import Span

_FANG = "# FANG\n\nDomain: AI agents. Evidence bar: arxiv OK."


def _span(i: int) -> Span:
    return Span(
        trace_id=f"t{i}",
        node_id=f"n{i}",
        kind="search.arxiv",  # type: ignore[arg-type]
        started_at=float(i),
        ended_at=float(i) + 0.1,
        verdict="ok",  # type: ignore[arg-type]
    )


def _build(tmp_path: Path, *, with_memory: bool = True) -> ProgressiveContextAssembler:
    fang_path = tmp_path / "FANG.md"
    fang_path.write_text(_FANG, encoding="utf-8")
    fang = FANGLoader(path=fang_path)
    buffer = WorkingBuffer(max_turns=2)
    memory: MemoryStore | None = None
    if with_memory:
        kb = KBStore(db_path=":memory:").open()
        memory = MemoryStore(kb)
        for i in range(10):
            memory.append(_span(i))
    return ProgressiveContextAssembler(fang=fang, buffer=buffer, memory=memory)


def test_assembler_includes_persona_and_memory_index(tmp_path: Path):
    assembler = _build(tmp_path)
    for i in range(3):
        assembler.buffer.add("user", f"turn {i}")
    ctx = assembler.assemble()
    assert "PERSONA" in ctx
    assert "Domain: AI agents" in ctx
    assert "MEMORY INDEX" in ctx
    assert "search.arxiv" in ctx
    assert "turn 2" in ctx  # most recent turn in buffer
    assert "turn 0" not in ctx  # fell out via WorkingBuffer compaction


def test_assembler_without_memory_still_works(tmp_path: Path):
    assembler = _build(tmp_path, with_memory=False)
    ctx = assembler.assemble()
    assert "PERSONA" in ctx
    assert "MEMORY INDEX" not in ctx


def test_compact_limit_controls_memory_lines(tmp_path: Path):
    assembler = _build(tmp_path)
    assembler.compact_limit = 3
    ctx = assembler.assemble()
    # Count how many memory-index lines appear (each line starts with '[').
    memory_section = ctx.split("MEMORY INDEX")[1].split("\n\n")[0]
    lines = [ln for ln in memory_section.splitlines() if ln.strip().startswith("[")]
    assert len(lines) == 3


def test_empty_buffer_and_empty_memory_still_assembles(tmp_path: Path):
    assembler = _build(tmp_path, with_memory=False)
    ctx = assembler.assemble()
    assert "PERSONA" in ctx
    # No crashes even with no RECENT TURNS section.
    assert "RECENT TURNS" not in ctx


def test_token_approx_is_monotonic():
    a = ProgressiveContextAssembler.token_approx("a" * 4)
    b = ProgressiveContextAssembler.token_approx("b" * 400)
    assert b > a
    assert a >= 1
