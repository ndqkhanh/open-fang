"""Pass@k and Pass^k metrics (Claw-Eval shape; plan.md §6, docs/38).

- ``Pass@k``: probability at least one of the first k runs succeeds, via the
  HumanEval unbiased estimator.
- ``Pass^k``: reliability — probability all k runs succeed simultaneously.
  Empirical rolling-window estimate when ≥k observations are present; falls
  back to (c/n)**k under the independence assumption when n < k.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import comb


@dataclass
class PasskSummary:
    k: int
    n_runs: int
    n_success: int
    pass_at_k: float
    pass_pow_k: float


def pass_at_k(n: int, c: int, k: int) -> float:
    if k <= 0:
        raise ValueError("k must be >= 1")
    if n <= 0:
        raise ValueError("n must be >= 1")
    if c < 0 or c > n:
        raise ValueError("c must be in [0, n]")
    if k > n:
        k = n
    if c > n - k:
        return 1.0
    return 1.0 - (comb(n - c, k) / comb(n, k))


def pass_pow_k(results: Sequence[bool], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be >= 1")
    n = len(results)
    if n == 0:
        return 0.0
    if n < k:
        p = sum(results) / n
        return p**k
    windows = 0
    all_ok = 0
    for i in range(n - k + 1):
        windows += 1
        if all(results[i : i + k]):
            all_ok += 1
    return all_ok / windows if windows else 0.0


def summarise(results: Sequence[bool], k: int) -> PasskSummary:
    n = len(results)
    c = sum(results)
    return PasskSummary(
        k=k,
        n_runs=n,
        n_success=c,
        pass_at_k=pass_at_k(n, c, k) if n > 0 else 0.0,
        pass_pow_k=pass_pow_k(results, k),
    )
