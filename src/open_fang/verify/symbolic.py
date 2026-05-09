"""Tier 4.5 — symbolic claim-number verifier (v6.2).

Between Tier-4 executable and Tier-5 critic. Catches claims whose NUMERIC
content is the fabrication point — e.g., "X is fivefold faster than Y"
where evidence shows 3×, not 5×.

Regex extraction of (multiplier, subject, object) triples; lookup in the
merged `structured_data` of cited evidence; compute observed ratio; compare
against claim's ratio within ±15% tolerance by default.

Runs only on `quantitative` claim-kind (per v4.1 router).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..models import Claim, Evidence

_MULTIPLIER_PATTERNS = {
    "twofold": 2.0,
    "threefold": 3.0,
    "fourfold": 4.0,
    "fivefold": 5.0,
    "sixfold": 6.0,
    "sevenfold": 7.0,
    "eightfold": 8.0,
    "ninefold": 9.0,
    "tenfold": 10.0,
    "hundredfold": 100.0,
    "double": 2.0,
    "triple": 3.0,
    "quadruple": 4.0,
    "half": 0.5,
    "halves": 0.5,
}

# `\b` after the multiplier char would require it to be a word char, which `×`
# is not. Drop the trailing word boundary; whitespace/punct/EOS terminates.
_NUM_MULTIPLIER_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*[x×](?=\s|$|[^\w])", re.IGNORECASE)
_NUM_FOLD_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*[-]?fold\b", re.IGNORECASE)


@dataclass
class NumericAssertion:
    claimed_ratio: float
    span: str


@dataclass
class SymbolicVerdict:
    passed: bool
    claimed_ratio: float | None = None
    observed_ratio: float | None = None
    reason: str = ""
    skipped: bool = False


def extract_numeric_assertions(claim_text: str) -> list[NumericAssertion]:
    """Find every numeric-ratio assertion in the claim text."""
    found: list[NumericAssertion] = []
    text = claim_text or ""

    # Pattern A: "N×" or "Nx"
    for m in _NUM_MULTIPLIER_RE.finditer(text):
        try:
            value = float(m.group(1))
            found.append(NumericAssertion(claimed_ratio=value, span=m.group(0)))
        except ValueError:
            pass

    # Pattern B: "N-fold" or "Nfold"
    for m in _NUM_FOLD_RE.finditer(text):
        try:
            value = float(m.group(1))
            found.append(NumericAssertion(claimed_ratio=value, span=m.group(0)))
        except ValueError:
            pass

    # Pattern C: word multipliers (fivefold, tenfold, double, half…)
    lowered = text.lower()
    for word, ratio in _MULTIPLIER_PATTERNS.items():
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            found.append(NumericAssertion(claimed_ratio=ratio, span=word))

    # Deduplicate (same claimed_ratio + span).
    seen: set[tuple[float, str]] = set()
    unique: list[NumericAssertion] = []
    for a in found:
        key = (a.claimed_ratio, a.span.lower())
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


def _observed_ratio_from_evidence(
    evidence_list: list[Evidence],
    claim: Claim,
) -> float | None:
    """Scan cited evidence's structured_data for two numeric values whose ratio
    can be compared. Heuristic: look for any pair of keys whose values form
    a numeric ratio; return the maximum ratio observed."""
    merged: dict[str, float] = {}
    by_id = {e.id: e for e in evidence_list}
    for eid in claim.evidence_ids:
        ev = by_id.get(eid)
        if ev is None:
            continue
        for k, v in (ev.structured_data or {}).items():
            if isinstance(v, (int, float)) and v > 0:
                merged[k] = float(v)

    if len(merged) < 2:
        return None

    values = list(merged.values())
    # The most-discriminating ratio is max/min (captures speedup / token ratio).
    hi, lo = max(values), min(values)
    if lo == 0:
        return None
    return hi / lo


class SymbolicVerifier:
    """Tier 4.5 — runs only on quantitative claims with numeric assertions."""

    def __init__(self, *, tolerance: float = 0.15) -> None:
        self.tolerance = tolerance

    def verify(self, claim: Claim, evidence: list[Evidence]) -> SymbolicVerdict:
        assertions = extract_numeric_assertions(claim.text)
        if not assertions:
            return SymbolicVerdict(passed=True, reason="no numeric assertions", skipped=True)

        observed = _observed_ratio_from_evidence(evidence, claim)
        if observed is None:
            return SymbolicVerdict(
                passed=True,
                reason="no structured_data to verify against",
                skipped=True,
            )

        # Check every assertion; fail if any diverges beyond tolerance.
        for a in assertions:
            # Accept either a:1 or 1:a mapping (we don't know which direction).
            ratio = a.claimed_ratio
            if ratio <= 0:
                continue
            forward_ok = abs(observed - ratio) / ratio <= self.tolerance
            inverse_ok = (
                abs(observed - (1.0 / ratio)) / (1.0 / ratio) <= self.tolerance
                if ratio >= 1.0
                else False
            )
            if not (forward_ok or inverse_ok):
                return SymbolicVerdict(
                    passed=False,
                    claimed_ratio=ratio,
                    observed_ratio=observed,
                    reason=(
                        f"claimed {ratio}× but observed ratio {observed:.2f} — "
                        f"divergence > ±{self.tolerance:.0%}"
                    ),
                )
        return SymbolicVerdict(
            passed=True,
            claimed_ratio=assertions[0].claimed_ratio,
            observed_ratio=observed,
            reason="all numeric assertions within tolerance",
        )
