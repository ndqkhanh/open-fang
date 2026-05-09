from __future__ import annotations

import pytest

from open_fang.synthesize.compression import (
    compress_markdown,
    token_estimate,
)

_VERBOSE = """# Briefing

Sure! In order to address this, I hope this helps. However, it is important to
note that the method basically improves. Additionally, furthermore, the results
are essentially strong.

- ReWOO decouples reasoning from observations. [1]
- Moreover, the approach improves throughput by 47%. [2]
"""


def test_standard_returns_input_unchanged():
    assert compress_markdown(_VERBOSE, mode="standard") == _VERBOSE


def test_terse_drops_filler_words():
    out = compress_markdown(_VERBOSE, mode="terse")
    for w in ("Sure!", "I hope this helps", "it is important to", "basically",
              "essentially"):
        assert w.lower() not in out.lower()


def test_terse_drops_connectives():
    out = compress_markdown(_VERBOSE, mode="terse")
    for w in ("However", "Moreover", "Furthermore", "Additionally"):
        assert w.lower() not in out.lower()


def test_terse_preserves_claims_and_citations():
    out = compress_markdown(_VERBOSE, mode="terse")
    assert "ReWOO decouples reasoning from observations" in out
    assert "[1]" in out
    assert "[2]" in out


def test_terse_achieves_length_reduction():
    raw_len = len(_VERBOSE)
    terse_len = len(compress_markdown(_VERBOSE, mode="terse"))
    # Terse should cut measurable length on verbose input.
    assert terse_len < raw_len * 0.85  # ≥15% reduction on this corpus


def test_ultra_more_aggressive_than_terse():
    terse = len(compress_markdown(_VERBOSE, mode="terse"))
    ultra = len(compress_markdown(_VERBOSE, mode="ultra"))
    assert ultra <= terse


def test_ultra_retains_claim_core_words():
    out = compress_markdown(_VERBOSE, mode="ultra")
    # Strong content words (nouns + verbs) survive.
    assert "ReWOO" in out
    assert "decouples" in out
    assert "reasoning" in out
    assert "[1]" in out


def test_token_estimate_monotonic():
    assert token_estimate("a" * 4) == 1
    assert token_estimate("a" * 400) == 100


def test_unknown_mode_raises():
    with pytest.raises(ValueError):
        compress_markdown("x", mode="gibberish")  # type: ignore[arg-type]
