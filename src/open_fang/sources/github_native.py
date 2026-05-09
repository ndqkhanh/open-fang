"""GithubNativeSource (v6.3) — Papers-With-Code + README extension.

Adds code-for-paper discovery and README fetch to the v1.2 GithubSource.
Uses Papers With Code's paper→repo linkage when available; falls back to
keyword search.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from ..models import Evidence, SourceRef
from .github import GithubSource

PWC_API = "https://paperswithcode.com/api/v1"


@dataclass
class CodeForPaper:
    arxiv_id: str
    repo_url: str
    stars: int | None


class GithubNativeSource(GithubSource):
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        token: str = "",
        timeout: float = 10.0,
    ) -> None:
        super().__init__(client=client, token=token, timeout=timeout)

    def find_code_for_paper(self, arxiv_id: str) -> list[CodeForPaper]:
        """Resolve arxiv_id → code repositories via Papers With Code."""
        url = f"{PWC_API}/papers/{arxiv_id}/repositories/"
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            data = resp.json() or {}
        except (httpx.HTTPError, ValueError):
            return []
        results = data.get("results", []) if isinstance(data, dict) else []
        out: list[CodeForPaper] = []
        for r in results:
            if not isinstance(r, dict):
                continue
            repo_url = r.get("url") or r.get("repo_url")
            if not repo_url:
                continue
            out.append(
                CodeForPaper(
                    arxiv_id=arxiv_id,
                    repo_url=str(repo_url),
                    stars=r.get("stars") if isinstance(r.get("stars"), int) else None,
                )
            )
        return out

    def fetch_repo_readme(self, repo_full_name: str) -> Evidence | None:
        """Fetch README for `owner/repo`; returns an Evidence with kind='github'."""
        url = f"https://api.github.com/repos/{repo_full_name}/readme"
        try:
            resp = self._client.get(url, headers={"Accept": "application/vnd.github.raw"})
            resp.raise_for_status()
            body = resp.text
        except httpx.HTTPError:
            return None
        if not body:
            return None
        return Evidence(
            source=SourceRef(
                kind="github",
                identifier=f"https://github.com/{repo_full_name}",
                title=repo_full_name,
                authors=[repo_full_name.split("/")[0]],
            ),
            content=body[:4000],
            channel="body",
        )
