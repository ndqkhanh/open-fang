"""GithubSource: code-for-paper discovery via the repositories search endpoint.

Yields Evidence with `kind='github'`, `content=` the repo description/README-ish
snippet returned by the search API. Reference-grade adapter; richer content
(README fetch) is a Phase-3+ extension.
"""
from __future__ import annotations

from typing import Any

import httpx

from ..models import Evidence, SourceRef

GITHUB_SEARCH = "https://api.github.com/search/repositories"


class GithubSource:
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        token: str = "",
        timeout: float = 10.0,
    ) -> None:
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = client or httpx.Client(timeout=timeout, headers=headers)

    def search(self, query: str, *, max_results: int = 5) -> list[Evidence]:
        params: dict[str, Any] = {
            "q": query,
            "per_page": max_results,
            "sort": "stars",
            "order": "desc",
        }
        resp = self._client.get(GITHUB_SEARCH, params=params)
        resp.raise_for_status()
        data = resp.json() or {}
        return [_repo_to_evidence(r) for r in data.get("items", []) if r.get("description")]

    def close(self) -> None:
        self._client.close()


def _repo_to_evidence(r: dict[str, Any]) -> Evidence:
    return Evidence(
        source=SourceRef(
            kind="github",
            identifier=r.get("html_url") or r.get("full_name", ""),
            title=r.get("full_name") or "",
            authors=[(r.get("owner") or {}).get("login", "")],
            published_at=(r.get("created_at") or "")[:10] or None,
        ),
        content=r.get("description") or "",
        channel="body",
        relevance=0.75,
    )
