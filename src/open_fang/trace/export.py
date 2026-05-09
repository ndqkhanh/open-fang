"""TrajectoryExporter — emit pipeline-result trajectories in a JSONL format
compatible with Hermes Agent's `tinker-atropos` submodule (v3-plan.md §3.W4).

v3.3 ships the emitter; v5.3 aligns the schema against Atropos's expected
inputs. The format is minimal JSON; consumers needing more fields can extend
the `TrajectoryEntry` dataclass and re-run.

Schema (one line per trajectory):
    {
      "trajectory_id": str,
      "brief": {"question": str, "target_length_words": int, "style": str},
      "dag_id": str,
      "plan_nodes": [{"id": str, "kind": str, "args": {...}}],
      "reward": float,           # == faithfulness_ratio
      "metrics": {
          "verified_claims": int,
          "total_claims": int,
          "mutation_warnings": int,
          "executable_failures": int,
          "parked_nodes": [str],
          "failed_nodes": [str]
      },
      "activated_skills": [str],
      "timestamp": str           # ISO-8601 UTC
    }
"""
from __future__ import annotations

import datetime as _dt
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from ..pipeline import PipelineResult


class AtroposSchemaError(ValueError):
    """Raised when a trajectory fails Atropos schema validation."""


_REQUIRED_TOP_KEYS = {
    "trajectory_id",
    "brief",
    "dag_id",
    "plan_nodes",
    "reward",
    "metrics",
    "activated_skills",
    "timestamp",
}
_REQUIRED_METRICS = {
    "verified_claims",
    "total_claims",
    "mutation_warnings",
    "executable_failures",
    "parked_nodes",
    "failed_nodes",
}


def validate_trajectory(payload: dict) -> list[str]:
    """Return a list of schema-violation messages (empty when valid)."""
    issues: list[str] = []
    missing = _REQUIRED_TOP_KEYS - set(payload)
    for k in sorted(missing):
        issues.append(f"missing top-level key: {k!r}")
    if isinstance(payload.get("reward"), (int, float)):
        r = float(payload["reward"])
        if not 0.0 <= r <= 1.0:
            issues.append(f"reward must be in [0.0, 1.0], got {r}")
    else:
        if "reward" in payload:
            issues.append(f"reward must be numeric, got {type(payload['reward']).__name__}")

    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        issues.append("metrics must be an object")
    else:
        metric_missing = _REQUIRED_METRICS - set(metrics)
        for k in sorted(metric_missing):
            issues.append(f"missing metrics key: {k!r}")
    return issues


@dataclass
class TrajectoryEntry:
    trajectory_id: str
    brief: dict
    dag_id: str
    plan_nodes: list[dict]
    reward: float
    metrics: dict
    activated_skills: list[str]
    timestamp: str

    def to_json(self) -> str:
        return json.dumps(self.__dict__, separators=(",", ":"))


class TrajectoryExporter:
    def export_trajectory(
        self,
        result: PipelineResult,
        *,
        plan_nodes: list[dict] | None = None,
    ) -> TrajectoryEntry:
        report = result.report
        now = _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"

        mutation_warnings = sum(
            1 for section in report.sections for claim in section.claims
            if claim.mutation_warning
        )
        executable_failures = sum(
            1 for section in report.sections for claim in section.claims
            if claim.executable_passed is False
        )

        return TrajectoryEntry(
            trajectory_id=uuid.uuid4().hex[:12],
            brief={
                "question": report.brief.question,
                "target_length_words": report.brief.target_length_words,
                "style": report.brief.style,
            },
            dag_id=report.dag_id,
            plan_nodes=plan_nodes or [],
            reward=float(report.faithfulness_ratio),
            metrics={
                "verified_claims": int(report.verified_claims),
                "total_claims": int(report.total_claims),
                "mutation_warnings": mutation_warnings,
                "executable_failures": executable_failures,
                "parked_nodes": list(result.parked_nodes),
                "failed_nodes": list(result.failed_nodes),
            },
            activated_skills=list(result.activated_skills),
            timestamp=now,
        )

    def export_batch(
        self,
        results: list[PipelineResult],
        *,
        output_path: Path | str,
    ) -> int:
        """Write one JSONL line per trajectory. Returns count written."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with path.open("w", encoding="utf-8") as f:
            for result in results:
                entry = self.export_trajectory(result)
                f.write(entry.to_json() + "\n")
                count += 1
        return count
