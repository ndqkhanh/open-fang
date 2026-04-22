from __future__ import annotations

from open_fang.kb.promote import promote_report
from open_fang.kb.store import KBStore
from open_fang.models import Brief, Claim, Evidence, Report, Section, SourceRef


def _ev(eid: str, ident: str, content: str, channel: str = "abstract") -> Evidence:
    return Evidence(
        id=eid,
        source=SourceRef(kind="arxiv", identifier=ident, title=ident, published_at="2023"),
        content=content,
        channel=channel,
    )


def _report(claims: list[Claim]) -> Report:
    return Report(
        brief=Brief(question="x"),
        sections=[Section(title="s", claims=claims)],
        references=[],
    )


def test_promote_writes_verified_claim_and_paper():
    kb = KBStore(db_path=":memory:").open()
    ev = _ev("e1", "arxiv:1", "ReWOO decouples reasoning.")
    report = _report(
        [Claim(text="ReWOO decouples reasoning.", evidence_ids=["e1"], verified=True)]
    )
    result = promote_report(report, [ev], kb)

    assert result.papers_added == 1
    assert result.claims_added == 1
    assert result.skipped_unverified == 0
    assert result.skipped_no_anchor == 0
    assert kb.count_papers() == 1
    assert kb.count_claims() == 1


def test_promote_skips_unverified_claim():
    kb = KBStore(db_path=":memory:").open()
    ev = _ev("e1", "arxiv:1", "x")
    report = _report(
        [Claim(text="x", evidence_ids=["e1"], verified=False)]
    )
    result = promote_report(report, [ev], kb)

    assert result.skipped_unverified == 1
    assert result.papers_added == 0
    assert kb.count_papers() == 0


def test_promote_dedupes_same_paper_across_claims():
    kb = KBStore(db_path=":memory:").open()
    ev = _ev("e1", "arxiv:1", "x")
    report = _report(
        [
            Claim(text="claim one", evidence_ids=["e1"], verified=True),
            Claim(text="claim two", evidence_ids=["e1"], verified=True),
        ]
    )
    result = promote_report(report, [ev], kb)

    assert result.papers_added == 1  # deduped
    assert result.claims_added == 2
    assert kb.count_claims() == 2


def test_promote_skips_claim_with_no_resolvable_anchor():
    kb = KBStore(db_path=":memory:").open()
    report = _report(
        [Claim(text="x", evidence_ids=["missing"], verified=True)]
    )
    result = promote_report(report, [], kb)

    assert result.skipped_no_anchor == 1
    assert kb.count_papers() == 0
