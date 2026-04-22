"""Compaction-resistance for FANG.md (plan.md §7 Phase-5 exit criterion).

Simulate 10 turns with a tight working-buffer cap; verify that the assembled
context always contains the FANG.md content verbatim, even after the buffer
has compacted most turns.
"""
from __future__ import annotations

from pathlib import Path

from open_fang.memory.context import ContextAssembler
from open_fang.memory.fang import FANGLoader
from open_fang.memory.working import WorkingBuffer

_FANG_SEED = "\n".join(
    [
        "# FANG seed",
        "",
        "Domain: AI agents; evidence bar: arxiv OK.",
        "Citation style: APA-inline + arxiv id.",
        "Preferred venues: NeurIPS, ICML, ICLR.",
    ]
)


def _assembler(tmp_path: Path) -> ContextAssembler:
    fang = tmp_path / "FANG.md"
    fang.write_text(_FANG_SEED, encoding="utf-8")
    return ContextAssembler(fang=FANGLoader(path=fang), buffer=WorkingBuffer(max_turns=3))


def test_persona_survives_10_turn_compaction(tmp_path: Path):
    asm = _assembler(tmp_path)
    for i in range(10):
        asm.buffer.add("user", f"turn {i}")
        asm.buffer.add("assistant", f"reply {i}")

    ctx = asm.assemble()

    # Persona header + full FANG.md contents appear verbatim.
    assert "# PERSONA (FANG.md, never compacted)" in ctx
    for line in _FANG_SEED.strip().splitlines():
        if line.strip():
            assert line in ctx, f"missing FANG.md line: {line!r}"

    # Compaction actually ran.
    assert asm.buffer.compacted_count > 0
    assert "[compacted:" in ctx
    # Only the most recent 3 turns are present verbatim.
    assert "turn 9" in ctx
    assert "turn 0" not in ctx


def test_empty_fang_produces_compact_context(tmp_path: Path):
    fang = tmp_path / "FANG.md"
    fang.write_text("", encoding="utf-8")
    asm = ContextAssembler(fang=FANGLoader(path=fang), buffer=WorkingBuffer(max_turns=2))
    asm.buffer.add("user", "only turn")
    ctx = asm.assemble()
    assert "PERSONA" not in ctx
    assert "only turn" in ctx


def test_persona_loaded_fresh_each_assemble(tmp_path: Path):
    fang = tmp_path / "FANG.md"
    fang.write_text("initial", encoding="utf-8")
    asm = ContextAssembler(fang=FANGLoader(path=fang), buffer=WorkingBuffer(max_turns=2))
    ctx1 = asm.assemble()
    assert "initial" in ctx1

    # User edits FANG.md mid-session.
    fang.write_text("updated persona content", encoding="utf-8")
    ctx2 = asm.assemble()
    assert "updated persona content" in ctx2
    assert "initial" not in ctx2
