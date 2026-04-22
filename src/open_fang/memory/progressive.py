"""ProgressiveContextAssembler: FANG.md + Tier A compact index + last-N raw turns.

Designed to deliver ≥5× token reduction vs a naive full-transcript context,
while preserving persona integrity across compaction events. Tier B/C are
reached via tool calls, not included in the always-in-context bundle.
"""
from __future__ import annotations

from dataclasses import dataclass

from .fang import FANGLoader
from .store import MemoryStore
from .working import WorkingBuffer


@dataclass
class ProgressiveContextAssembler:
    fang: FANGLoader
    buffer: WorkingBuffer
    memory: MemoryStore | None = None
    compact_limit: int = 20

    def assemble(self) -> str:
        parts: list[str] = []
        persona = self.fang.load().strip()
        if persona:
            parts.append("# PERSONA (FANG.md, never compacted)\n" + persona)

        if self.memory is not None:
            index = self.memory.compact_index(limit=self.compact_limit)
            if index:
                parts.append(
                    "# MEMORY INDEX (Tier A — newest first)\n"
                    + "\n".join(index)
                )

        summary = self.buffer.summary()
        if summary:
            parts.append(summary)

        if self.buffer.turns:
            parts.append("# RECENT TURNS")
            for turn in self.buffer.turns:
                parts.append(f"[{turn.role}] {turn.content}")

        return "\n\n".join(parts)

    @staticmethod
    def token_approx(text: str) -> int:
        """Stable char-based token approximation (1 token ≈ 4 chars)."""
        return max(1, len(text) // 4)
