"""ExecutableVerifier — Tier 4 of the hardened verifier.

For quantitative claims, a reproduction-script skill emits a Python
assertion (the `Vcode` shape from arxiv:2604.18292). The assertion runs
against an `evidence` dict built from merged `structured_data` across cited
evidence. Assertion failure → the claim is downgraded to unverified.

Two execution modes:
  - in_process=True (default in tests): restricted `exec()` namespace. Fast.
  - in_process=False: subprocess with -I flag + timeout. Slower but sandboxed.

The restricted namespace bans `__builtins__` except a small safe subset. Net
IO, os access, and filesystem calls are *not* blocked in in-process mode —
user-authored scripts should stick to arithmetic + comparisons on `evidence`.
Production deployments should prefer subprocess mode.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Any

from ..models import Claim, Evidence

# Small set of builtins safe for assertion expressions.
_SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "AssertionError": AssertionError,
}


@dataclass
class ExecutionResult:
    passed: bool
    error: str | None = None
    stdout: str = ""


class ExecutableVerifier:
    def __init__(self, *, in_process: bool = True, timeout_s: float = 2.0) -> None:
        self.in_process = in_process
        self.timeout_s = timeout_s

    def verify(
        self,
        claim: Claim,
        evidence: list[Evidence],
        assertion_script: str,
    ) -> ExecutionResult:
        """Run `assertion_script` with `evidence` bound to merged structured_data."""
        merged = _merge_structured(claim, evidence)
        if self.in_process:
            return self._run_in_process(assertion_script, merged)
        return self._run_subprocess(assertion_script, merged)

    def _run_in_process(self, script: str, evidence_dict: dict[str, Any]) -> ExecutionResult:
        local_ns: dict[str, Any] = {"evidence": evidence_dict}
        global_ns: dict[str, Any] = {"__builtins__": _SAFE_BUILTINS}
        try:
            exec(script, global_ns, local_ns)  # noqa: S102
        except AssertionError as exc:
            return ExecutionResult(passed=False, error=f"AssertionError: {exc}")
        except Exception as exc:  # noqa: BLE001
            return ExecutionResult(passed=False, error=f"{type(exc).__name__}: {exc}")
        return ExecutionResult(passed=True)

    def _run_subprocess(self, script: str, evidence_dict: dict[str, Any]) -> ExecutionResult:
        import json

        full_script = (
            "import json, sys\n"
            f"evidence = json.loads({json.dumps(json.dumps(evidence_dict))})\n"
            + script
        )
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-c", full_script],
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(passed=False, error="timeout")
        if proc.returncode != 0:
            err = (proc.stderr.strip().splitlines() or [""])[-1]
            return ExecutionResult(passed=False, error=err, stdout=proc.stdout)
        return ExecutionResult(passed=True, stdout=proc.stdout)


def _merge_structured(claim: Claim, evidence: list[Evidence]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    by_id = {e.id: e for e in evidence}
    for eid in claim.evidence_ids:
        ev = by_id.get(eid)
        if ev is None:
            continue
        for k, v in ev.structured_data.items():
            merged[k] = v  # later cited-evidence wins on key collision
    return merged
