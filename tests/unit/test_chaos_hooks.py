from __future__ import annotations

import random

from open_fang.scheduler.chaos import ChaosInjector, ChaosRule


def test_empty_env_yields_no_rules():
    inj = ChaosInjector.from_env("")
    assert inj.rules == []
    assert inj.enabled() is False
    assert inj.should_fire("network_drop") is False


def test_parses_multi_rule_env():
    inj = ChaosInjector.from_env("network_drop:0.2;memory_drop:0.1")
    kinds = [r.kind for r in inj.rules]
    assert kinds == ["network_drop", "memory_drop"]
    assert abs(inj.probability("network_drop") - 0.2) < 1e-9
    assert abs(inj.probability("memory_drop") - 0.1) < 1e-9


def test_rejects_out_of_range_probability():
    inj = ChaosInjector.from_env("network_drop:1.5;memory_drop:-0.2;network_drop:0.3")
    assert len(inj.rules) == 1
    assert inj.rules[0].probability == 0.3


def test_should_fire_deterministic_with_rng():
    rng = random.Random(42)
    inj = ChaosInjector(rules=[ChaosRule(kind="network_drop", probability=0.5)], rng=rng)
    # Deterministic given the seed — count fires over 1000 draws.
    fires = sum(1 for _ in range(1000) if inj.should_fire("network_drop"))
    # At p=0.5, the count should be around 500 with plenty of tolerance.
    assert 400 <= fires <= 600


def test_probability_zero_never_fires():
    inj = ChaosInjector(rules=[ChaosRule(kind="network_drop", probability=0.0)])
    assert not any(inj.should_fire("network_drop") for _ in range(100))


def test_probability_one_always_fires():
    inj = ChaosInjector(rules=[ChaosRule(kind="memory_drop", probability=1.0)])
    assert all(inj.should_fire("memory_drop") for _ in range(50))


def test_unknown_kind_reports_zero_probability():
    inj = ChaosInjector.from_env("network_drop:0.5")
    assert inj.probability("not_a_real_kind") == 0.0
    assert inj.should_fire("not_a_real_kind") is False
