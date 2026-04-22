from __future__ import annotations

from open_fang.kb.decontamination import DecontaminationScanner
from open_fang.kb.store import KBStore
from open_fang.models import SourceRef


def _seed(kb: KBStore, ident: str, abstract: str) -> None:
    kb.upsert_paper(
        SourceRef(kind="arxiv", identifier=ident, title=ident, authors=["X"]),
        abstract=abstract,
    )


def test_scanner_flags_swebench_fingerprint():
    kb = KBStore(db_path=":memory:").open()
    _seed(kb, "arxiv:a", "We evaluate on SWEBench-Verified, reporting pass@1.")
    _seed(kb, "arxiv:b", "A paper about cats.")
    report = DecontaminationScanner().scan(kb)
    assert report.scanned == 2
    assert report.flagged_ids == ["arxiv:a"]


def test_scanner_flags_multiple_fingerprints_in_same_paper():
    kb = KBStore(db_path=":memory:").open()
    _seed(kb, "arxiv:x", "Reports on BFCL V4 and τ²-Bench together.")
    report = DecontaminationScanner().scan(kb)
    assert "arxiv:x" in report.flagged_ids
    # At least two distinct fingerprints fired.
    assert sum(1 for c in report.fingerprint_hits.values() if c >= 1) >= 2


def test_scanner_clean_kb_returns_zero_flags():
    kb = KBStore(db_path=":memory:").open()
    _seed(kb, "arxiv:clean", "ReWOO decouples reasoning from observations.")
    report = DecontaminationScanner().scan(kb)
    assert report.flagged_ids == []
    assert all(c == 0 for c in report.fingerprint_hits.values())


def test_scanner_custom_fingerprints():
    kb = KBStore(db_path=":memory:").open()
    _seed(kb, "arxiv:y", "Uses the SecretBench-2026 evaluation split.")
    scanner = DecontaminationScanner(fingerprints=(r"SecretBench",))
    assert scanner.scan(kb).flagged_ids == ["arxiv:y"]


def test_text_has_fingerprint_standalone():
    scanner = DecontaminationScanner()
    assert scanner.text_has_fingerprint("SWEBench-Verified + BFCL V4")  # 2 hits
    assert scanner.text_has_fingerprint("unrelated content") == []


def test_scanner_case_insensitive():
    kb = KBStore(db_path=":memory:").open()
    _seed(kb, "arxiv:z", "evaluated on swebench_lite and CLAWBENCH.")
    report = DecontaminationScanner().scan(kb)
    assert "arxiv:z" in report.flagged_ids
