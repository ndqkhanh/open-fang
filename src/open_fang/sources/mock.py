"""MockSource: deterministic evidence returned without network access."""
from __future__ import annotations

from ..models import Evidence, SourceRef


class MockSource:
    """Returns a small deterministic evidence set for any query."""

    def __init__(self, canned: list[Evidence] | None = None) -> None:
        self._canned = canned

    def search(self, query: str, *, max_results: int = 3) -> list[Evidence]:
        if self._canned is not None:
            return list(self._canned)
        q = query.strip() or "ai-agents"
        return [
            Evidence(
                source=SourceRef(
                    kind="arxiv",
                    identifier=f"arxiv:mock.{i:04d}",
                    title=f"Mock paper {i} about {q}",
                    authors=[f"Author {i}"],
                    published_at="2026-04",
                ),
                content=(
                    f"Abstract: this mock paper discusses {q}. "
                    "It presents a scaffold-level claim used in OpenFang tests."
                ),
                channel="abstract",
                relevance=1.0 - 0.1 * i,
            )
            for i in range(max_results)
        ]
