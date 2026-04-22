"""WorkingBuffer: capped turn buffer with compaction of oldest turns.

Compaction in v1 is lossy summarization: older turns are replaced by a single
`[compacted: N earlier turns]` marker. The design constraint from plan.md §3.3
is that the persona partition (FANG.md) is held in a separate, never-compacted
slot (see ContextAssembler), not in this buffer.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Turn:
    role: str  # "user" | "assistant" | "tool"
    content: str


@dataclass
class WorkingBuffer:
    """Rolling turn buffer. When more than `max_turns` are added, older turns
    are replaced by a compacted marker that preserves only an aggregate count."""

    max_turns: int = 6
    turns: list[Turn] = field(default_factory=list)
    compacted_count: int = 0

    def add(self, role: str, content: str) -> None:
        self.turns.append(Turn(role=role, content=content))
        self._compact_if_needed()

    def _compact_if_needed(self) -> None:
        if len(self.turns) <= self.max_turns:
            return
        overflow = len(self.turns) - self.max_turns
        dropped = self.turns[:overflow]
        self.compacted_count += len(dropped)
        self.turns = self.turns[overflow:]

    def summary(self) -> str:
        if self.compacted_count == 0:
            return ""
        return f"[compacted: {self.compacted_count} earlier turns]"
