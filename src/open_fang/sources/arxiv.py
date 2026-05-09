"""ArxivSource: Atom-feed client for arxiv.org.

Uses httpx; the client is injectable so tests can use httpx.MockTransport
to hit canned XML without touching the network.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import httpx

from ..models import Evidence, SourceRef

ARXIV_API = "http://export.arxiv.org/api/query"
_ATOM = "{http://www.w3.org/2005/Atom}"


class ArxivSource:
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        email: str = "",
        timeout: float = 10.0,
    ) -> None:
        self._client = client or httpx.Client(
            timeout=timeout,
            headers={"User-Agent": f"OpenFang/0.1 ({email})"} if email else None,
        )

    def search(self, query: str, *, max_results: int = 5) -> list[Evidence]:
        params: dict[str, Any] = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
        }
        resp = self._client.get(ARXIV_API, params=params)
        resp.raise_for_status()
        return _parse_atom(resp.text)

    def close(self) -> None:
        self._client.close()


def _parse_atom(xml_text: str) -> list[Evidence]:
    root = ET.fromstring(xml_text)
    evidence: list[Evidence] = []
    for entry in root.findall(f"{_ATOM}entry"):
        title = _text(entry, f"{_ATOM}title").strip()
        summary = _text(entry, f"{_ATOM}summary").strip()
        published = _text(entry, f"{_ATOM}published").strip() or None
        authors = [
            _text(a, f"{_ATOM}name").strip()
            for a in entry.findall(f"{_ATOM}author")
            if _text(a, f"{_ATOM}name").strip()
        ]
        arxiv_id = _extract_arxiv_id(_text(entry, f"{_ATOM}id"))
        if not arxiv_id or not summary:
            continue
        evidence.append(
            Evidence(
                source=SourceRef(
                    kind="arxiv",
                    identifier=f"arxiv:{arxiv_id}",
                    title=title,
                    authors=authors,
                    published_at=published,
                ),
                content=summary,
                channel="abstract",
                relevance=1.0,
            )
        )
    return evidence


def _text(elem: ET.Element, tag: str) -> str:
    child = elem.find(tag)
    return (child.text or "") if child is not None and child.text is not None else ""


def _extract_arxiv_id(id_url: str) -> str:
    # Typical: http://arxiv.org/abs/2305.18323v1 → "2305.18323"
    token = id_url.rsplit("/", 1)[-1] if id_url else ""
    if not token:
        return ""
    # Strip trailing version suffix (vN).
    if "v" in token:
        base, _, suffix = token.rpartition("v")
        if suffix.isdigit():
            return base
    return token
