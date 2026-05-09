from __future__ import annotations

from open_fang.eval.passk import pass_at_k, pass_pow_k, summarise


def test_pass_at_k_all_success():
    assert pass_at_k(n=5, c=5, k=3) == 1.0


def test_pass_at_k_no_success():
    assert pass_at_k(n=5, c=0, k=3) == 0.0


def test_pass_at_k_partial():
    # HumanEval estimator: Pass@1 with 2 of 4 successes = 2/4 = 0.5.
    assert pass_at_k(n=4, c=2, k=1) == 0.5


def test_pass_at_k_clamps_k_to_n():
    assert pass_at_k(n=3, c=3, k=10) == 1.0


def test_pass_at_k_rejects_invalid_inputs():
    import pytest

    with pytest.raises(ValueError):
        pass_at_k(n=0, c=0, k=1)
    with pytest.raises(ValueError):
        pass_at_k(n=3, c=4, k=1)
    with pytest.raises(ValueError):
        pass_at_k(n=3, c=1, k=0)


def test_pass_pow_k_all_true_returns_one():
    assert pass_pow_k([True] * 10, k=3) == 1.0


def test_pass_pow_k_all_false_returns_zero():
    assert pass_pow_k([False] * 10, k=3) == 0.0


def test_pass_pow_k_rolling_window_mixed():
    # 6 results, 3 length-4 windows: [T,T,T,T], [T,T,T,F], [T,T,F,T]
    # Only the first window has all-true → 1/3.
    results = [True, True, True, True, False, True]
    assert abs(pass_pow_k(results, k=4) - (1 / 3)) < 1e-9


def test_pass_pow_k_falls_back_when_fewer_than_k():
    # n=2, k=3, c=1, p=0.5, fallback = 0.125
    assert abs(pass_pow_k([True, False], k=3) - 0.125) < 1e-9


def test_summarise_combines_metrics():
    s = summarise([True, True, False, True], k=2)
    assert s.k == 2
    assert s.n_runs == 4
    assert s.n_success == 3
    assert 0.0 <= s.pass_at_k <= 1.0
    assert 0.0 <= s.pass_pow_k <= 1.0
