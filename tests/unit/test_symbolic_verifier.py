from __future__ import annotations

from open_fang.models import Claim, Evidence, SourceRef
from open_fang.verify.symbolic import SymbolicVerifier, extract_numeric_assertions


def _claim(text: str, evidence_id: str = "e1") -> Claim:
    return Claim(text=text, evidence_ids=[evidence_id])


def _ev(id_: str, data: dict) -> Evidence:
    return Evidence(
        id=id_,
        source=SourceRef(kind="arxiv", identifier="x"),
        content="body",
        structured_data=data,
    )


def test_extract_x_multiplier():
    a = extract_numeric_assertions("ReWOO is 5x faster")
    assert any(abs(x.claimed_ratio - 5.0) < 1e-9 for x in a)


def test_extract_cross_multiplier():
    a = extract_numeric_assertions("ReWOO is 5× faster")
    assert any(abs(x.claimed_ratio - 5.0) < 1e-9 for x in a)


def test_extract_fold():
    a = extract_numeric_assertions("5-fold reduction")
    assert any(abs(x.claimed_ratio - 5.0) < 1e-9 for x in a)


def test_extract_word_multipliers():
    a = extract_numeric_assertions("a fivefold improvement")
    assert any(abs(x.claimed_ratio - 5.0) < 1e-9 for x in a)
    b = extract_numeric_assertions("it does double the speed")
    assert any(abs(x.claimed_ratio - 2.0) < 1e-9 for x in b)
    c = extract_numeric_assertions("halves the memory")
    assert any(abs(x.claimed_ratio - 0.5) < 1e-9 for x in c)


def test_no_numeric_assertions_skips_verify():
    v = SymbolicVerifier()
    result = v.verify(_claim("it's elegant"), [_ev("e1", {"a": 100, "b": 20})])
    assert result.skipped is True
    assert result.passed is True


def test_no_structured_data_skips_verify():
    v = SymbolicVerifier()
    result = v.verify(_claim("5x faster"), [_ev("e1", {})])
    assert result.skipped is True


def test_claim_within_tolerance_passes():
    # Evidence ratio = 600/120 = 5.0; claim of "5x faster" within tolerance.
    v = SymbolicVerifier()
    result = v.verify(
        _claim("5x faster"),
        [_ev("e1", {"react_tokens": 600, "rewoo_tokens": 120})],
    )
    assert result.passed is True
    assert result.skipped is False


def test_tenfold_fabrication_caught():
    # Evidence ratio = 5.0; claim of "tenfold" diverges (100% off).
    v = SymbolicVerifier()
    result = v.verify(
        _claim("tenfold improvement"),
        [_ev("e1", {"a": 600, "b": 120})],
    )
    assert result.passed is False
    assert result.claimed_ratio == 10.0
    assert abs(result.observed_ratio - 5.0) < 0.01


def test_tolerance_expansion():
    # Evidence ratio = 4.5; claim of 5× — within 15% tolerance (5*1.15=5.75).
    v = SymbolicVerifier(tolerance=0.15)
    result = v.verify(
        _claim("5x faster"),
        [_ev("e1", {"a": 450, "b": 100})],
    )
    assert result.passed is True


def test_inverse_direction_accepted():
    """5× faster can be expressed either as A/B=5 or B/A=5."""
    v = SymbolicVerifier()
    result = v.verify(
        _claim("5x faster"),
        [_ev("e1", {"hi": 100, "lo": 500})],
    )
    assert result.passed is True  # ratio 5, forward_ok matches
