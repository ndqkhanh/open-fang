"""SourceRouter: dispatch a scheduler node to the right external-source adapter.

Each source (Arxiv / S2 / Github / Mock) satisfies the `SearchSource` protocol
(a `search(query, *, max_results)` method). The router maps node kinds to the
correct source and falls through to a default when a specific one is missing.
"""
from __future__ import annotations

from typing import Protocol

from ..models import Evidence


class SearchSource(Protocol):
    def search(self, query: str, *, max_results: int = ...) -> list[Evidence]: ...


class SourceRouter:
    def __init__(
        self,
        *,
        arxiv: SearchSource | None = None,
        s2: SearchSource | None = None,
        github: SearchSource | None = None,
        fallback: SearchSource | None = None,
    ) -> None:
        self.arxiv = arxiv
        self.s2 = s2
        self.github = github
        self.fallback = fallback

    def for_kind(self, kind: str) -> SearchSource | None:
        if kind == "search.arxiv":
            return self.arxiv or self.fallback
        if kind == "search.semantic_scholar":
            return self.s2 or self.fallback
        if kind == "search.github":
            return self.github or self.fallback
        return self.fallback

    def search(self, kind: str, query: str, *, max_results: int = 5) -> list[Evidence]:
        source = self.for_kind(kind)
        if source is None:
            return []
        return source.search(query, max_results=max_results)


def from_single(source: SearchSource) -> SourceRouter:
    """Wrap one source so every search kind routes to it (scheduler back-compat)."""
    return SourceRouter(fallback=source)
