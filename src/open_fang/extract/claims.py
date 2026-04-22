"""Claim extraction: paper section → list[Claim] with evidence spans."""
from __future__ import annotations

from ..models import Claim, Evidence


class ClaimExtractor:
    """MVP: one claim per evidence, lexically anchored."""

    def extract(self, evidence_list: list[Evidence]) -> list[Claim]:
        claims: list[Claim] = []
        for e in evidence_list:
            text = _first_sentence(e.content)
            if text:
                claims.append(Claim(text=text, evidence_ids=[e.id]))
        return claims


def _first_sentence(content: str) -> str:
    content = content.strip()
    if not content:
        return ""
    for sep in (". ", ".\n"):
        idx = content.find(sep)
        if idx != -1:
            return content[: idx + 1].strip()
    return content[:200].strip()
