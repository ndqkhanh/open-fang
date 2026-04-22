from __future__ import annotations

from open_fang.kb.promote import can_promote
from open_fang.models import Claim


def test_unverified_claim_cannot_promote(canned_evidence):
    claim = Claim(text="x", evidence_ids=["e1"], verified=False)
    assert can_promote(claim, canned_evidence) is False


def test_verified_claim_with_source_can_promote(canned_evidence):
    claim = Claim(text="x", evidence_ids=["e1"], verified=True)
    assert can_promote(claim, canned_evidence) is True


def test_verified_claim_without_bound_evidence_cannot_promote(canned_evidence):
    claim = Claim(text="x", evidence_ids=["missing"], verified=True)
    assert can_promote(claim, canned_evidence) is False
