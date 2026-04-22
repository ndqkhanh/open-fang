from __future__ import annotations

import json

from harness_core.models import MockLLM

from open_fang.models import Brief, Claim, Report, Section
from open_fang.pipeline import PipelineResult
from open_fang.skills.diagnostician import Diagnostician


def _result(faithfulness: float, rejection_note: str = "") -> PipelineResult:
    claim = Claim(text="claim", evidence_ids=[], verified=faithfulness >= 0.90)
    if not claim.verified and rejection_note:
        claim.verification_note = rejection_note
    return PipelineResult(
        report=Report(
            brief=Brief(question="q"),
            sections=[Section(title="s", claims=[claim])],
            references=[],
            faithfulness_ratio=faithfulness,
            verified_claims=1 if claim.verified else 0,
            total_claims=1,
        ),
        parked_nodes=[],
        failed_nodes=[],
        downgraded_claims=[],
        activated_skills=["citation-extraction"],
    )


def test_diagnose_returns_empty_when_all_results_are_strong():
    report = Diagnostician().diagnose([_result(1.0), _result(0.95)])
    assert report.weaknesses == []
    assert report.sample_size == 0


def test_heuristic_fallback_extracts_recurring_note():
    results = [
        _result(0.50, "claim has no lexical overlap with cited evidence"),
        _result(0.60, "claim has no lexical overlap with cited evidence"),
        _result(0.55, "claim has no lexical overlap with cited evidence"),
    ]
    report = Diagnostician().diagnose(results)
    assert report.sample_size == 3
    assert len(report.weaknesses) == 1
    w = report.weaknesses[0]
    assert "lexical overlap" in w.pattern
    assert w.proposed_fix
    assert "citation-extraction" in w.affected_skills


def test_llm_driven_diagnosis_parses_structured_json():
    payload = {
        "weaknesses": [
            {
                "pattern": "claims overstate numeric results",
                "proposed_fix": "activate reproduction-script skill earlier",
                "affected_skills": ["claim-localization"],
            }
        ]
    }
    llm = MockLLM(scripted_outputs=[json.dumps(payload)])
    report = Diagnostician(llm=llm).diagnose([_result(0.50, "note")])
    assert len(report.weaknesses) == 1
    assert report.weaknesses[0].pattern.startswith("claims overstate")
    assert report.weaknesses[0].affected_skills == ["claim-localization"]


def test_llm_invalid_json_falls_back_to_empty():
    llm = MockLLM(scripted_outputs=["not json"])
    report = Diagnostician(llm=llm).diagnose([_result(0.50, "note")])
    assert report.weaknesses == []
    assert report.sample_size == 1  # still counts the weak sample
