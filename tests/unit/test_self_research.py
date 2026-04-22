from __future__ import annotations

from pathlib import Path

from open_fang.pipeline import OpenFangPipeline
from open_fang.scheduler.engine import SchedulerEngine
from open_fang.self_research import (
    extract_open_questions,
    extract_open_questions_from_file,
    run_self_research,
    write_candidates_markdown,
)
from open_fang.sources.mock import MockSource

_MD = """
# v6 plan

## 1. TL;DR
Some content.

## 8. Open questions

1. **HAFC classifier granularity** — 12 or more primitives?
2. **Confidence signal source** — which LLM metadata to tap?
3. **Tolerance in symbolic verifier**.

## 9. Other section
Unrelated body.
"""


def test_extract_questions_from_numbered_list():
    qs = extract_open_questions(_MD)
    assert len(qs) == 3
    normalized_texts = [q.normalized for q in qs]
    assert any("HAFC" in n for n in normalized_texts)
    assert any("Confidence" in n for n in normalized_texts)
    # Every normalized question ends with a `?` (question-shaped).
    assert all(n.endswith("?") for n in normalized_texts)


def test_extract_questions_stops_at_next_section():
    qs = extract_open_questions(_MD)
    # Section 9 content should not leak into the questions.
    raws = [q.raw for q in qs]
    assert not any("Other section" in r for r in raws)
    assert not any("Unrelated" in r for r in raws)


def test_extract_bullet_fallback():
    md = """
## 8. Open questions

- **First bullet** — some note
- **Second bullet**

## 9. Next
"""
    qs = extract_open_questions(md)
    assert len(qs) == 2
    assert any("First" in q.normalized for q in qs)


def test_no_open_questions_section_returns_empty():
    assert extract_open_questions("# Plan\n\nNo questions here.") == []


def test_extract_from_file(tmp_path: Path):
    path = tmp_path / "plan.md"
    path.write_text(_MD, encoding="utf-8")
    qs = extract_open_questions_from_file(path)
    assert len(qs) == 3


def test_run_self_research_produces_reports_per_plan(canned_evidence, tmp_path: Path):
    plan_1 = tmp_path / "v1.md"
    plan_1.write_text(_MD, encoding="utf-8")

    pipeline = OpenFangPipeline(scheduler=SchedulerEngine(source=MockSource(canned=canned_evidence)))
    reports = run_self_research(pipeline, [plan_1])
    assert len(reports) == 1
    r = reports[0]
    assert len(r.questions) == 3
    assert len(r.results) == 3
    # Every pipeline result is populated.
    assert all(res.report is not None for res in r.results)


def test_write_candidates_markdown_produces_parseable_file(canned_evidence, tmp_path: Path):
    plan = tmp_path / "v1.md"
    plan.write_text(_MD, encoding="utf-8")

    pipeline = OpenFangPipeline(scheduler=SchedulerEngine(source=MockSource(canned=canned_evidence)))
    reports = run_self_research(pipeline, [plan])
    out = write_candidates_markdown(reports, tmp_path / "candidates.md")

    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "OpenFang Self-Research Report" in body
    assert str(plan) in body
    # Questions / candidates section present.
    assert "Candidate workstream seeds" in body
