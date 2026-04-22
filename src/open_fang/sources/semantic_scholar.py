"""S2Source: Semantic Scholar Graph API client.

Free endpoint: https://api.semanticscholar.org/graph/v1/paper/search
An API key is recommended for higher rate limits (`x-api-key` header).
"""
from __future__ import annotations

from typing import Any

import httpx

from ..models import Evidence, SourceRef

S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "title,abstract,authors,year,externalIds,venue"


class S2Source:
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        api_key: str = "",
        timeout: float = 10.0,
    ) -> None:
        headers = {"x-api-key": api_key} if api_key else None
        self._client = client or httpx.Client(timeout=timeout, headers=headers)

    def search(self, query: str, *, max_results: int = 5) -> list[Evidence]:
        params: dict[str, Any] = {
            "query": query,
            "limit": max_results,
            "fields": _FIELDS,
        }
        resp = self._client.get(S2_SEARCH, params=params)
        resp.raise_for_status()
        data = resp.json() or {}
        return [_paper_to_evidence(p) for p in data.get("data", []) if p.get("abstract")]

    def close(self) -> None:
        self._client.close()


def _paper_to_evidence(p: dict[str, Any]) -> Evidence:
    ext_ids = p.get("externalIds") or {}
    arxiv_id = ext_ids.get("ArXiv") or ""
    identifier = f"arxiv:{arxiv_id}" if arxiv_id else f"s2:{p.get('paperId', '')}"
    authors = [a.get("name", "") for a in (p.get("authors") or []) if a.get("name")]
    year = p.get("year")
    return Evidence(
        source=SourceRef(
            kind="arxiv" if arxiv_id else "s2",
            identifier=identifier,
            title=p.get("title") or "",
            authors=authors,
            published_at=str(year) if year else None,
        ),
        content=p.get("abstract") or "",
        channel="abstract",
        relevance=1.0,
    )
