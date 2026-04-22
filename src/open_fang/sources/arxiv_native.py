"""ArxivNativeSource (v6.3) — BibTeX + reference-graph extension over ArxivSource.

Adds two capabilities on top of the v1.2 ArxivSource:
    fetch_bibtex(arxiv_id)      → raw BibTeX string
    fetch_references(arxiv_id)  → list of referenced arxiv_ids (best-effort parse)

The reference-graph endpoint isn't a first-class arxiv API — we parse BibTeX
citations or use the Semantic Scholar fallback when available. For v6.3 MVP,
the parser extracts arxiv_ids from any bibtex-ish body text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from .arxiv import ArxivSource

ARXIV_BIBTEX = "https://arxiv.org/bibtex"
_ARXIV_ID_RE = re.compile(r"\b(\d{4}\.\d{4,5})(?:v\d+)?\b")


@dataclass
class ReferenceEdge:
    src_arxiv_id: str
    dst_arxiv_id: str


class ArxivNativeSource(ArxivSource):
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        email: str = "",
        timeout: float = 10.0,
    ) -> None:
        super().__init__(client=client, email=email, timeout=timeout)

    def fetch_bibtex(self, arxiv_id: str) -> str:
        """Return raw BibTeX for the given arxiv id (or '' on failure)."""
        url = f"{ARXIV_BIBTEX}/{arxiv_id}"
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPError:
            return ""

    def fetch_references(self, arxiv_id: str) -> list[ReferenceEdge]:
        """Best-effort: parse arxiv_ids out of the paper's BibTeX context.

        arxiv.org/bibtex usually only returns the paper's own BibTeX; for
        reference graphs a proper endpoint is S2. v6.3 MVP returns edges
        from any arxiv_ids found in the bibtex body (excluding the source id).
        """
        body = self.fetch_bibtex(arxiv_id)
        refs = {m.group(1) for m in _ARXIV_ID_RE.finditer(body)}
        refs.discard(arxiv_id)
        return [ReferenceEdge(src_arxiv_id=arxiv_id, dst_arxiv_id=r) for r in sorted(refs)]
