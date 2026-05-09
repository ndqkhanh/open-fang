"""Session retrieval memory: vector + FTS over the agent's own history.

Skeleton — ships in Phase 5.
"""
from __future__ import annotations


class RetrievalMemory:
    def lookup(self, query: str, *, k: int = 5) -> list[str]:
        return []
