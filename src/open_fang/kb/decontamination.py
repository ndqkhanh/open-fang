"""Decontamination: flag KB papers that cite known test-set fingerprints.

Adapted from arxiv:2604.05013 (Atomic Skills) Appendix C.1. The fingerprint
list covers well-known agent benchmarks whose test splits leak into many
pre-training corpora. A flagged paper stays searchable but is excluded from
evaluation baselines.

v2.7 MVP is in-memory (file-loaded on open); v3 moves the list to its own
SQLite table so user-specific fingerprints can be managed via the API.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .store import KBStore

# Canonical benchmark fingerprints — URLs, repo paths, or commit-id regexes
# associated with evaluation-set leakage.
_DEFAULT_FINGERPRINTS: tuple[str, ...] = (
    # SWE-bench splits
    r"swebench[\s\-_/]?verified",
    r"swebench[\s\-_/]?lite",
    # ClawBench / Claw-Eval
    r"clawbench",
    r"claw[\s\-_]eval",
    # τ²-Bench (tolerate τ² / tau2 / t2 and any whitespace/hyphen)
    r"(?:tau2|τ²)[\s\-_]?bench",
    # BFCL V4 (tolerate space or hyphen between BFCL and V4)
    r"bfcl[\s\-_]?v4",
    r"berkeley[\s\-_]function[\s\-_]calling[\s\-_]leaderboard",
    # GAIA + HLE agent evals
    r"gaia[\s\-_]benchmark",
    r"gaia[\s\-_]test",
    r"humanity[\s\-_]last[\s\-_]exam",
    # Raw commit-id fingerprints (40-hex from public eval repos)
    r"\b[a-f0-9]{40}\b(?=.*swebench)",
)


@dataclass
class DecontaminationReport:
    scanned: int
    flagged_ids: list[str]
    fingerprint_hits: dict[str, int]  # fingerprint → paper count


class DecontaminationScanner:
    def __init__(self, *, fingerprints: tuple[str, ...] = _DEFAULT_FINGERPRINTS) -> None:
        self._patterns = [re.compile(fp, re.IGNORECASE) for fp in fingerprints]
        self._fingerprint_labels = list(fingerprints)

    def scan(self, kb: KBStore) -> DecontaminationReport:
        flagged: list[str] = []
        hits: dict[str, int] = {fp: 0 for fp in self._fingerprint_labels}
        scanned = 0
        for paper_id in kb.list_paper_ids():
            scanned += 1
            ev = kb.get_paper(paper_id)
            if ev is None:
                continue
            found_any = False
            for label, pattern in zip(self._fingerprint_labels, self._patterns):
                if pattern.search(ev.content):
                    hits[label] += 1
                    found_any = True
            if found_any:
                flagged.append(paper_id)
        return DecontaminationReport(
            scanned=scanned,
            flagged_ids=flagged,
            fingerprint_hits=hits,
        )

    def text_has_fingerprint(self, text: str) -> list[str]:
        """Return the list of fingerprint labels matched in `text`."""
        return [
            label
            for label, pattern in zip(self._fingerprint_labels, self._patterns)
            if pattern.search(text or "")
        ]
