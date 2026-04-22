"""MutationProbe — Tier 2 of the hardened verifier.

For claims with numeric/quantitative content, generate 3-5 mutants
(digit-swap, sign-flip, quantifier-reverse, unit-swap) and ask the LLM judge
to classify each against the original evidence. The judge must return
SUPPORTED for the ORIGINAL claim and NOT_SUPPORTED for every mutant; any
mutant that the judge also marks SUPPORTED indicates the judge is not
actually reading the evidence at the numeric level.

Per plan.md §10 risks: Tier 2 emits a WARNING, not a veto. The LLM judge
(Tier 3) remains authoritative for accept/reject.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from harness_core.models import LLMProvider

from ..models import Claim, Evidence
from .llm_judge import LLMJudge

_NUMERIC_RE = re.compile(r"\b\d+(?:\.\d+)?\b")

_SIGN_FLIP = {
    "reduces": "increases",
    "reduce": "increase",
    "decreases": "increases",
    "decrease": "increase",
    "increases": "reduces",
    "increase": "reduce",
    "improves": "degrades",
    "improve": "degrade",
    "degrades": "improves",
    "degrade": "improve",
    "outperforms": "underperforms",
    "lower": "higher",
    "higher": "lower",
    "more": "less",
    "less": "more",
    "faster": "slower",
    "slower": "faster",
    "better": "worse",
    "worse": "better",
}

_QUANTIFIER_FLIP = {
    "all": "none",
    "none": "all",
    "always": "never",
    "never": "always",
    "fivefold": "half",
    "tenfold": "half",
    "twofold": "half",
    "doubles": "halves",
    "halves": "doubles",
}


@dataclass
class MutationResult:
    claim_text: str
    mutants: list[str] = field(default_factory=list)
    mutant_classes: list[str] = field(default_factory=list)
    judge_verdicts: list[bool] = field(default_factory=list)  # True = judge said SUPPORTED
    original_supported: bool | None = None

    @property
    def resistance(self) -> float:
        """Fraction of mutants correctly marked NOT_SUPPORTED by the judge."""
        if not self.judge_verdicts:
            return 1.0
        rejected = sum(1 for v in self.judge_verdicts if not v)
        return rejected / len(self.judge_verdicts)

    @property
    def distinguishable(self) -> bool:
        """True iff the judge marked the original SUPPORTED and every mutant NOT_SUPPORTED."""
        if self.original_supported is not True:
            return False
        return all(v is False for v in self.judge_verdicts)


def generate_mutants(claim_text: str, *, max_mutants: int = 5) -> list[tuple[str, str]]:
    """Return up to `max_mutants` (mutant_text, class) pairs for a claim."""
    out: list[tuple[str, str]] = []

    # 1. Digit swap on the first numeric token.
    m = _NUMERIC_RE.search(claim_text)
    if m:
        original = m.group()
        swapped = _digit_swap(original)
        if swapped != original:
            out.append(
                (
                    claim_text[: m.start()] + swapped + claim_text[m.end() :],
                    "digit-swap",
                )
            )

    # 2. Sign-flip on a signal verb.
    for word, replacement in _SIGN_FLIP.items():
        pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
        if pattern.search(claim_text):
            flipped = pattern.sub(replacement, claim_text, count=1)
            if flipped != claim_text:
                out.append((flipped, "sign-flip"))
                break

    # 3. Quantifier reversal.
    for word, replacement in _QUANTIFIER_FLIP.items():
        pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
        if pattern.search(claim_text):
            flipped = pattern.sub(replacement, claim_text, count=1)
            if flipped != claim_text:
                out.append((flipped, "quantifier-reverse"))
                break

    # 4. Unit swap: % ↔ points.
    if "%" in claim_text:
        out.append((claim_text.replace("%", " points"), "unit-swap"))
    elif " points" in claim_text:
        out.append((claim_text.replace(" points", "%"), "unit-swap"))

    # 5. Numeric magnitude flip (double it).
    m2 = _NUMERIC_RE.search(claim_text)
    if m2:
        original = m2.group()
        try:
            val = float(original)
            flipped = str(int(val * 10)) if val.is_integer() else f"{val * 10:.2f}"
            mutant = claim_text[: m2.start()] + flipped + claim_text[m2.end() :]
            if mutant != claim_text and mutant not in [t for t, _ in out]:
                out.append((mutant, "magnitude-flip"))
        except ValueError:
            pass

    return out[:max_mutants]


def has_mutable_content(claim_text: str) -> bool:
    """Return True if the claim contains numeric or signal-verb content worth mutating."""
    if _NUMERIC_RE.search(claim_text):
        return True
    lowered = claim_text.lower()
    return any(w in lowered for w in _SIGN_FLIP) or any(w in lowered for w in _QUANTIFIER_FLIP)


def _digit_swap(token: str) -> str:
    """Swap the first digit with a different digit (deterministic: +1 mod 10)."""
    for i, ch in enumerate(token):
        if ch.isdigit():
            new_digit = str((int(ch) + 1) % 10)
            return token[:i] + new_digit + token[i + 1 :]
    return token


class MutationProbe:
    """Tier-2 verifier: generates mutants + asks the judge to distinguish them."""

    def __init__(self, llm: LLMProvider) -> None:
        self.judge = LLMJudge(llm)

    def probe(self, claim: Claim, evidence: list[Evidence]) -> MutationResult:
        if not has_mutable_content(claim.text):
            return MutationResult(claim_text=claim.text)
        pairs = generate_mutants(claim.text)
        by_id = {e.id: e for e in evidence}
        cited = [by_id[eid].content for eid in claim.evidence_ids if eid in by_id]
        if not cited:
            return MutationResult(claim_text=claim.text, mutants=[m for m, _ in pairs])

        original_verdict = self.judge.judge(claim.text, cited)
        mutants = [m for m, _ in pairs]
        classes = [c for _, c in pairs]
        verdicts = [self.judge.judge(m, cited).supported for m in mutants]

        return MutationResult(
            claim_text=claim.text,
            mutants=mutants,
            mutant_classes=classes,
            judge_verdicts=verdicts,
            original_supported=original_verdict.supported,
        )
