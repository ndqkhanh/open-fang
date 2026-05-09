"""ContextAssembler: combine persona (FANG.md, never compacted) + working buffer.

The assembled context always has the persona content verbatim at the top; the
working buffer is compacted as it fills. This realizes the plan.md §3.3
"persona partition never compacted" guarantee at the code level.
"""
from __future__ import annotations

from dataclasses import dataclass

from .fang import FANGLoader
from .working import WorkingBuffer


@dataclass
class ContextAssembler:
    fang: FANGLoader
    buffer: WorkingBuffer

    def assemble(self) -> str:
        persona = self.fang.load().strip()
        parts: list[str] = []
        if persona:
            parts.append("# PERSONA (FANG.md, never compacted)\n" + persona)
        summary = self.buffer.summary()
        if summary:
            parts.append(summary)
        for turn in self.buffer.turns:
            parts.append(f"[{turn.role}] {turn.content}")
        return "\n\n".join(parts)
