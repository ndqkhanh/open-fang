"""ClaimKindRouter (v4.1) — route claims to the right verifier tier subset.

Classifies each claim as one of: quantitative / qualitative / citation /
methodological. Returns the active verifier tiers per kind (per v4-plan.md §W5).

Rule-based classifier (no LLM calls). Ambiguous claims escalate to the full
5-tier pipeline.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from ..models import Claim

ClaimKind = Literal["quantitative", "qualitative", "citation", "methodological", "ambiguous"]

_QUANT_TOKENS = re.compile(
    r"\b("
    r"\d+(?:\.\d+)?%?"
    r"|fivefold|tenfold|twofold|half|double|triple"
    r"|outperforms?|improves?|reduces?|increases?|decreases?|degrades?"
    r"|better|worse|faster|slower|higher|lower"
    r")\b",
    re.IGNORECASE,
)
_CITATION_TOKENS = re.compile(r"\b(?:cites?|refer(s|enced)?|according to|per \(?\w)", re.IGNORECASE)
_METHOD_TOKENS = re.compile(
    r"\b(method|methodology|experiment|benchmark|evaluation|reproduc(e|ible|ibility)|protocol|setup)\b",
    re.IGNORECASE,
)


@dataclass
class ClassifiedClaim:
    kind: ClaimKind
    reason: str


# v4.1 tier activation map. `lexical` runs on every claim (always-on).
_TIER_MAP: dict[ClaimKind, tuple[str, ...]] = {
    "quantitative": ("lexical", "mutation", "llm_judge", "executable", "critic"),
    "qualitative": ("lexical", "llm_judge", "critic"),
    "citation": ("lexical", "llm_judge", "critic"),
    "methodological": ("lexical", "mutation", "llm_judge", "critic"),
    "ambiguous": ("lexical", "mutation", "llm_judge", "executable", "critic"),
}


def classify(claim: Claim) -> ClassifiedClaim:
    text = claim.text or ""
    quant = bool(_QUANT_TOKENS.search(text))
    citation = bool(_CITATION_TOKENS.search(text))
    method = bool(_METHOD_TOKENS.search(text))

    # Precedence: quantitative > methodological > citation > qualitative
    # (Quantitative + any other is still quantitative.)
    if quant:
        return ClassifiedClaim(kind="quantitative", reason="numeric/comparative tokens present")
    if method:
        return ClassifiedClaim(kind="methodological", reason="methodology tokens present")
    if citation:
        return ClassifiedClaim(kind="citation", reason="citation tokens present")
    if text.strip():
        return ClassifiedClaim(kind="qualitative", reason="no trigger tokens")
    return ClassifiedClaim(kind="ambiguous", reason="empty or unparseable")


def tiers_for(kind: ClaimKind) -> tuple[str, ...]:
    return _TIER_MAP[kind]


def tiers_for_claim(claim: Claim) -> tuple[str, ...]:
    return tiers_for(classify(claim).kind)
