from __future__ import annotations

import json
from pathlib import Path

from open_fang.models import Brief, Claim, Report, Section
from open_fang.pipeline import PipelineResult
from open_fang.trace.export import (
    TrajectoryExporter,
    validate_trajectory,
)


def _result(
    *,
    faithfulness: float = 1.0,
    total: int = 3,
    verified: int = 3,
    mutation_warn: int = 0,
    exec_failures: int = 0,
    skills: list[str] | None = None,
) -> PipelineResult:
    claims = []
    for i in range(total):
        c = Claim(text=f"claim {i}", evidence_ids=["e1"], verified=i < verified)
        if i < mutation_warn:
            c.mutation_warning = True
        if i < exec_failures:
            c.executable_passed = False
        claims.append(c)
    return PipelineResult(
        report=Report(
            brief=Brief(question="rewoo", style="standard", target_length_words=500),
            sections=[Section(title="s", claims=claims)],
            references=[],
            faithfulness_ratio=faithfulness,
            verified_claims=verified,
            total_claims=total,
            dag_id="d-abc",
            trace_id="t-abc",
        ),
        parked_nodes=[],
        failed_nodes=[],
        downgraded_claims=[],
        activated_skills=skills or [],
    )


def test_export_trajectory_returns_valid_entry():
    entry = TrajectoryExporter().export_trajectory(_result(skills=["citation-extraction"]))
    assert entry.reward == 1.0
    assert entry.metrics["verified_claims"] == 3
    assert entry.metrics["total_claims"] == 3
    assert entry.activated_skills == ["citation-extraction"]
    assert entry.brief["question"] == "rewoo"
    assert validate_trajectory(json.loads(entry.to_json())) == []


def test_export_captures_mutation_warnings_and_executable_failures():
    entry = TrajectoryExporter().export_trajectory(
        _result(total=4, verified=2, mutation_warn=2, exec_failures=1)
    )
    assert entry.metrics["mutation_warnings"] == 2
    assert entry.metrics["executable_failures"] == 1
    assert entry.metrics["verified_claims"] == 2
    assert entry.metrics["total_claims"] == 4


def test_export_batch_writes_jsonl(tmp_path: Path):
    results = [_result() for _ in range(3)]
    out = tmp_path / "trajectories.jsonl"
    count = TrajectoryExporter().export_batch(results, output_path=out)
    assert count == 3
    lines = [ln for ln in out.read_text().splitlines() if ln.strip()]
    assert len(lines) == 3
    for line in lines:
        assert validate_trajectory(json.loads(line)) == []


def test_validate_catches_missing_top_keys():
    issues = validate_trajectory({"reward": 0.9})
    assert any("trajectory_id" in i for i in issues)
    assert any("brief" in i for i in issues)


def test_validate_catches_missing_metrics_keys():
    issues = validate_trajectory(
        {
            "trajectory_id": "t",
            "brief": {},
            "dag_id": "d",
            "plan_nodes": [],
            "reward": 0.5,
            "metrics": {"verified_claims": 1},
            "activated_skills": [],
            "timestamp": "now",
        }
    )
    assert any("total_claims" in i for i in issues)


def test_validate_catches_reward_out_of_range():
    payload = {
        "trajectory_id": "t",
        "brief": {},
        "dag_id": "d",
        "plan_nodes": [],
        "reward": 1.5,
        "metrics": dict.fromkeys(
            ["verified_claims", "total_claims", "mutation_warnings",
             "executable_failures", "parked_nodes", "failed_nodes"],
            0,
        ),
        "activated_skills": [],
        "timestamp": "now",
    }
    assert any("reward" in i for i in validate_trajectory(payload))


def test_empty_batch_writes_no_lines(tmp_path: Path):
    out = tmp_path / "empty.jsonl"
    n = TrajectoryExporter().export_batch([], output_path=out)
    assert n == 0
    assert out.read_text() == ""
