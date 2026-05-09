"""v2.4 exit criterion (v2-plan.md §8): mutation-resistance ≥ 85% on corpus.

Runs each `MutationCase` through the full hardened verifier (Tiers 1-4).
Fabricated cases must be caught (verified=False OR mutation_warning=True OR
executable_passed=False). Honest cases must not be incorrectly blocked.
"""
from __future__ import annotations

import json

from harness_core.models import MockLLM

from open_fang.models import Brief, Claim, Report, Section
from open_fang.verify.claim_verifier import ClaimVerifier, ExecutableProbe
from open_fang.verify.executable import ExecutableVerifier
from open_fang.verify.mutation import MutationProbe
from tests.fixtures.mutation_claims import CASES, EVIDENCE

CATCH_RATE_FLOOR = 0.85


def _verifier(mutation_support: bool = True) -> ClaimVerifier:
    """Build a verifier where every LLM call returns SUPPORTED.

    With `mutation_support=True` the judge can't distinguish mutants, which
    *should* raise the mutation_warning for truly fabricated claims.
    """
    mutation = MutationProbe(
        MockLLM(
            scripted_outputs=[json.dumps({"verdict": "supported", "span": ""})] * 500
        )
    ) if mutation_support else None
    judge_llm = MockLLM(
        scripted_outputs=[json.dumps({"verdict": "supported", "span": ""})] * 500
    )
    return ClaimVerifier(
        llm=judge_llm,
        mutation_probe=mutation,
        executable_verifier=ExecutableVerifier(),
    )


def test_mutation_corpus_catches_fabrications_at_floor():
    claims = []
    script_map: dict[str, str] = {}
    for case in CASES:
        claim = Claim(text=case.claim_text, evidence_ids=[EVIDENCE.id])
        claims.append((claim, case))
        if case.script is not None:
            script_map[claim.id] = case.script

    report = Report(
        brief=Brief(question="mutation corpus"),
        sections=[Section(title="s", claims=[c for c, _ in claims])],
        references=[],
    )

    verifier = _verifier()
    verifier.executable_probe = ExecutableProbe(scripts=script_map)
    verifier.verify(report, [EVIDENCE])

    fabricated = [c for c, case in claims if case.is_fabricated]
    # A fabrication is "caught" when the hardened verifier either:
    #   - vetoes it (verified=False),
    #   - flags it via Tier 2 mutation warning, or
    #   - rejects its executable assertion.
    caught = [
        c for c in fabricated
        if (not c.verified)
        or c.mutation_warning
        or c.executable_passed is False
    ]
    catch_rate = len(caught) / len(fabricated) if fabricated else 0.0
    assert catch_rate >= CATCH_RATE_FLOOR, (
        f"mutation catch rate {catch_rate:.2%} < {CATCH_RATE_FLOOR:.0%} "
        f"({len(caught)}/{len(fabricated)} caught)"
    )


def test_honest_claims_are_not_blocked():
    claims = []
    script_map: dict[str, str] = {}
    for case in CASES:
        claim = Claim(text=case.claim_text, evidence_ids=[EVIDENCE.id])
        claims.append((claim, case))
        if case.script is not None:
            script_map[claim.id] = case.script

    report = Report(
        brief=Brief(question="honest-claims check"),
        sections=[Section(title="s", claims=[c for c, _ in claims])],
        references=[],
    )
    verifier = _verifier()
    verifier.executable_probe = ExecutableProbe(scripts=script_map)
    verifier.verify(report, [EVIDENCE])

    honest = [c for c, case in claims if not case.is_fabricated]
    blocked = [c for c in honest if not c.verified]
    assert not blocked, (
        f"{len(blocked)}/{len(honest)} honest claims incorrectly blocked: "
        f"{[c.verification_note for c in blocked]}"
    )


def test_mutation_warning_fires_on_fabrications_with_numeric_content():
    """When the judge is permissive, fabricated numeric claims should at
    minimum carry `mutation_warning=True` even if Tier 3 passes them."""
    claims = []
    for case in CASES:
        if not case.is_fabricated:
            continue
        claim = Claim(text=case.claim_text, evidence_ids=[EVIDENCE.id])
        claims.append(claim)

    report = Report(
        brief=Brief(question="warning check"),
        sections=[Section(title="s", claims=claims)],
        references=[],
    )

    # No executable probe here — isolate Tier 2 signal.
    mutation = MutationProbe(
        MockLLM(scripted_outputs=[json.dumps({"verdict": "supported", "span": ""})] * 500)
    )
    judge_llm = MockLLM(
        scripted_outputs=[json.dumps({"verdict": "supported", "span": ""})] * 500
    )
    verifier = ClaimVerifier(llm=judge_llm, mutation_probe=mutation)
    verifier.verify(report, [EVIDENCE])

    # At least half the fabricated claims with mutable content must carry the warning.
    from open_fang.verify.mutation import has_mutable_content

    mutable = [c for c in claims if has_mutable_content(c.text)]
    warned = [c for c in mutable if c.mutation_warning]
    assert len(warned) >= len(mutable) // 2, (
        f"only {len(warned)}/{len(mutable)} mutable fabrications got mutation_warning"
    )
