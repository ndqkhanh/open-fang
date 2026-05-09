from __future__ import annotations

from open_fang.models import Claim, Evidence, SourceRef
from open_fang.verify.executable import ExecutableVerifier


def _claim(eid: str = "e1") -> Claim:
    return Claim(text="a quantitative claim", evidence_ids=[eid])


def _evidence(data: dict) -> list[Evidence]:
    return [
        Evidence(
            id="e1",
            source=SourceRef(kind="arxiv", identifier="arxiv:x"),
            content="evidence body",
            structured_data=data,
        )
    ]


def test_in_process_passes_valid_assertion():
    v = ExecutableVerifier()
    ev = _evidence({"rewoo_tokens": 120, "react_tokens": 600})
    script = "ratio = evidence['react_tokens'] / evidence['rewoo_tokens']\nassert 4.0 <= ratio <= 6.0, 'ratio mismatch'"
    result = v.verify(_claim(), ev, script)
    assert result.passed is True
    assert result.error is None


def test_in_process_fails_bad_assertion_with_error_message():
    v = ExecutableVerifier()
    ev = _evidence({"rewoo_tokens": 400, "react_tokens": 600})
    script = "ratio = evidence['react_tokens'] / evidence['rewoo_tokens']\nassert ratio >= 4.0, 'claimed fivefold, ratio only 1.5'"
    result = v.verify(_claim(), ev, script)
    assert result.passed is False
    assert result.error is not None
    assert "AssertionError" in result.error


def test_in_process_script_with_key_error_fails_gracefully():
    v = ExecutableVerifier()
    ev = _evidence({"only_key": 1})
    script = "assert evidence['missing_key'] == 5"
    result = v.verify(_claim(), ev, script)
    assert result.passed is False
    assert "KeyError" in (result.error or "")


def test_in_process_safe_namespace_blocks_import():
    v = ExecutableVerifier()
    ev = _evidence({"x": 1})
    script = "import os\nassert os.path.exists('/')"
    result = v.verify(_claim(), ev, script)
    assert result.passed is False
    # The safe namespace has no `__import__`; script must fail with NameError
    # or similar.
    assert result.error is not None


def test_merged_structured_data_across_cited_evidence():
    v = ExecutableVerifier()
    # Two evidence items with different structured_data keys.
    e1 = Evidence(
        id="e1",
        source=SourceRef(kind="arxiv", identifier="x"),
        content="a",
        structured_data={"a": 1},
    )
    e2 = Evidence(
        id="e2",
        source=SourceRef(kind="arxiv", identifier="y"),
        content="b",
        structured_data={"b": 2},
    )
    claim = Claim(text="q", evidence_ids=["e1", "e2"])
    script = "assert evidence['a'] + evidence['b'] == 3"
    result = v.verify(claim, [e1, e2], script)
    assert result.passed is True


def test_subprocess_mode_passes_valid_assertion():
    v = ExecutableVerifier(in_process=False, timeout_s=5.0)
    ev = _evidence({"n": 42})
    script = "assert evidence['n'] == 42"
    result = v.verify(_claim(), ev, script)
    assert result.passed is True


def test_subprocess_mode_fails_on_timeout():
    v = ExecutableVerifier(in_process=False, timeout_s=0.5)
    # Infinite loop — subprocess must time out cleanly.
    result = v.verify(_claim(), _evidence({"x": 1}), "while True:\n    pass")
    assert result.passed is False
    assert result.error == "timeout"
