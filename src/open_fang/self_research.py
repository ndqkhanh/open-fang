"""Self-research loop (v6.5) — OpenFang researches its own plan files.

Extracts "open questions" sections from version-plan markdown, converts each
to a `Brief`, runs the pipeline on all of them, and emits a consolidated
"next-version candidates" report.

Unique to OpenFang: we're a research agent whose narrow domain includes
research-agent research. No other tool in the ecosystem has this property.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .models import Brief
from .pipeline import OpenFangPipeline, PipelineResult

# Match just the heading line itself (no trailing cross-line greediness).
_OPEN_QUESTIONS_HEADING_RE = re.compile(
    r"^ *##?\s+\d+\.?\s*Open\s+[Qq]uestions[^\n]*$",
    re.MULTILINE,
)
_NEXT_HEADING_RE = re.compile(r"^ *##?\s+\d+\.?\s+\S[^\n]*$", re.MULTILINE)
_NUMBERED_ITEM_RE = re.compile(r"^\s*\d+\.\s+\*\*(.+?)\*\*", re.MULTILINE)
_BULLET_ITEM_RE = re.compile(r"^\s*-\s+\*\*(.+?)\*\*", re.MULTILINE)


@dataclass
class OpenQuestion:
    raw: str
    normalized: str  # cleaned title fragment suitable as a Brief question


@dataclass
class SelfResearchReport:
    plan_path: str
    questions: list[OpenQuestion] = field(default_factory=list)
    results: list[PipelineResult] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "plan_path": self.plan_path,
            "total_questions": len(self.questions),
            "verified_claims_total": sum(r.report.verified_claims for r in self.results),
            "total_claims": sum(r.report.total_claims for r in self.results),
            "candidates": self.candidates,
        }


def extract_open_questions(markdown: str) -> list[OpenQuestion]:
    """Find the 'Open Questions' section and pull numbered/bulleted items."""
    heading_match = _OPEN_QUESTIONS_HEADING_RE.search(markdown)
    if heading_match is None:
        return []
    start = heading_match.end()
    # End at the next top-level numbered heading OR end-of-doc.
    end_match = _NEXT_HEADING_RE.search(markdown, pos=start + 1)
    body = markdown[start : end_match.start() if end_match else len(markdown)]

    out: list[OpenQuestion] = []
    for m in _NUMBERED_ITEM_RE.finditer(body):
        raw = m.group(0).strip()
        title = m.group(1).strip().rstrip(".")
        out.append(OpenQuestion(raw=raw, normalized=_normalize_question(title)))
    if out:
        return out
    # Fall back to bullet items.
    for m in _BULLET_ITEM_RE.finditer(body):
        raw = m.group(0).strip()
        title = m.group(1).strip().rstrip(".")
        out.append(OpenQuestion(raw=raw, normalized=_normalize_question(title)))
    return out


def _normalize_question(fragment: str) -> str:
    """Convert a `**Title**` fragment into a research-able question string."""
    fragment = fragment.replace("*", "").strip()
    if not fragment.endswith("?"):
        fragment = f"How should OpenFang handle: {fragment}?"
    return fragment


def extract_open_questions_from_file(path: Path | str) -> list[OpenQuestion]:
    return extract_open_questions(Path(path).read_text(encoding="utf-8"))


def run_self_research(
    pipeline: OpenFangPipeline,
    plan_paths: Iterable[Path | str],
) -> list[SelfResearchReport]:
    """Run pipeline on every open question extracted from each plan file."""
    reports: list[SelfResearchReport] = []
    for path in plan_paths:
        p = Path(path)
        questions = extract_open_questions_from_file(p)
        report = SelfResearchReport(plan_path=str(p), questions=questions)
        for q in questions:
            result = pipeline.run(Brief(question=q.normalized, target_length_words=600))
            report.results.append(result)
            # Candidates: verified claims from high-faithfulness runs.
            if result.report.faithfulness_ratio >= 0.9:
                for section in result.report.sections:
                    for claim in section.claims:
                        if claim.verified:
                            report.candidates.append(claim.text)
        reports.append(report)
    return reports


def write_candidates_markdown(reports: list[SelfResearchReport], output_path: Path | str) -> Path:
    """Emit a human-readable summary of candidates for the next-version plan."""
    lines = [
        "# OpenFang Self-Research Report",
        "",
        "Auto-generated candidates for the next version's workstream catalog.",
        "",
    ]
    for report in reports:
        summary = report.summary()
        lines.append(f"## Plan: {summary['plan_path']}")
        lines.append(f"- Open questions extracted: {summary['total_questions']}")
        lines.append(
            f"- Pipeline verified claims: "
            f"{summary['verified_claims_total']}/{summary['total_claims']}"
        )
        lines.append("")
        lines.append("### Candidate workstream seeds")
        if not report.candidates:
            lines.append("- *(none — all questions produced low-confidence output)*")
        else:
            seen: set[str] = set()
            for c in report.candidates:
                if c in seen:
                    continue
                seen.add(c)
                lines.append(f"- {c}")
        lines.append("")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
