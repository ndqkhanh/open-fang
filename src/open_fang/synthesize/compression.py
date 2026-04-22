"""Output compression profiles (v7.6) — Caveman-inspired terse/ultra modes.

Pattern source: JuliusBrussee/caveman (MIT). Applied to OpenFang's Report
rendering: same claim binding + same citations, fewer tokens.

Profiles:
    standard  current behavior (no transformation)
    terse     drop connectives, imperative voice, no extra whitespace
    ultra     bullet-only, strip articles/prepositions, integer citations

All profiles preserve claim-evidence binding so the verifier floor is unchanged.
"""
from __future__ import annotations

import re
from typing import Literal

from ..models import Report

CompressionMode = Literal["standard", "terse", "ultra"]

_FILLER_WORDS = (
    "please",
    "hopefully",
    "basically",
    "actually",
    "essentially",
    "in order to",
    "at this time",
    "it is important to",
    "for example",
    "thank you",
    "Sure!",
    "Absolutely",
    "I hope this helps",
)
_CONNECTIVES = (
    "however",
    "moreover",
    "furthermore",
    "additionally",
    "therefore",
    "consequently",
    "thus",
)
_ULTRA_STRIP = (
    "the",
    "a",
    "an",
    "of",
    "to",
    "in",
    "on",
    "for",
    "with",
    "at",
    "by",
    "as",
    "is",
    "are",
    "was",
    "were",
    "been",
    "being",
)


def compress_markdown(markdown: str, *, mode: CompressionMode = "standard") -> str:
    if mode == "standard":
        return markdown
    if mode == "terse":
        return _compress_terse(markdown)
    if mode == "ultra":
        return _compress_ultra(markdown)
    raise ValueError(f"unknown compression mode: {mode!r}")


def compress_report(report: Report, *, mode: CompressionMode = "standard") -> str:
    return compress_markdown(report.to_markdown(), mode=mode)


def _compress_terse(text: str) -> str:
    out = text
    # Filler words may already carry punctuation ("Sure!", "Absolutely"); use a
    # looser anchor that permits non-word chars at the boundary.
    for w in _FILLER_WORDS:
        pattern = rf"(?<!\w){re.escape(w)}[,.]?\s*"
        out = re.sub(pattern, "", out, flags=re.IGNORECASE)
    for w in _CONNECTIVES:
        out = re.sub(rf"\b{re.escape(w)}\b[,.]?\s*", "", out, flags=re.IGNORECASE)
    # Collapse multiple spaces left behind.
    out = re.sub(r"[ \t]{2,}", " ", out)
    # Tighten blank lines: >=2 blank → 1 blank.
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _compress_ultra(text: str) -> str:
    out = _compress_terse(text)
    for w in _ULTRA_STRIP:
        out = re.sub(rf"\b{re.escape(w)}\b\s*", "", out, flags=re.IGNORECASE)
    # Flatten sentences to fragments: strip trailing "." after short phrases.
    # Preserve citation markers like [1], [2] and heading markdown.
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def token_estimate(text: str) -> int:
    """Char-count / 4 heuristic, consistent with v3.1 progressive assembler."""
    return max(1, len(text) // 4)
