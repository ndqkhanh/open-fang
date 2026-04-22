from __future__ import annotations

import json

from harness_core.models import MockLLM

from open_fang.models import Claim, Evidence, SourceRef
from open_fang.verify.mutation import (
    MutationProbe,
    generate_mutants,
    has_mutable_content,
)


def test_has_mutable_content_detects_numbers_and_signal_verbs():
    assert has_mutable_content("ReWOO reduces tokens by 5x")
    assert has_mutable_content("The method improves accuracy")
    assert has_mutable_content("20% gain")
    assert has_mutable_content("never reaches that bound")
    assert not has_mutable_content("a purely qualitative description of the architecture")


def test_generate_mutants_produces_multiple_classes():
    src = "ReWOO reduces tokens by 47 percent relative to ReAct, improving throughput."
    mutants = generate_mutants(src)
    classes = {c for _, c in mutants}
    # Digit-swap (on the 47) and sign-flip (on 'reduces') should both fire.
    assert "digit-swap" in classes
    assert "sign-flip" in classes
    # Mutants differ from the original and from each other.
    texts = [t for t, _ in mutants]
    assert all(t != src for t in texts)
    assert len(texts) == len(set(texts))


def test_generate_mutants_empty_when_no_mutable_content():
    assert generate_mutants("a purely qualitative description") == []


def test_digit_swap_changes_first_digit():
    mutants = generate_mutants("improvement of 45% over the baseline")
    digit_swap = [t for t, c in mutants if c == "digit-swap"]
    assert digit_swap
    assert "45" not in digit_swap[0]  # swapped


def test_sign_flip_applies_to_known_verbs():
    mutants = generate_mutants("the method improves accuracy on all benchmarks")
    sign = [t for t, c in mutants if c == "sign-flip"]
    assert sign
    assert "improves" not in sign[0].lower()


def test_unit_swap_percent_to_points():
    mutants = generate_mutants("gain of 5%")
    swapped = [t for t, c in mutants if c == "unit-swap"]
    assert swapped
    assert "points" in swapped[0]


def _probe_claim() -> Claim:
    return Claim(text="ReWOO reduces tokens fivefold.", evidence_ids=["e1"])


def _evidence() -> list[Evidence]:
    return [
        Evidence(
            id="e1",
            source=SourceRef(kind="arxiv", identifier="arxiv:rewoo"),
            content="ReWOO reduces tokens fivefold relative to ReAct.",
        )
    ]


def test_probe_distinguishable_when_judge_separates_original_from_mutants():
    # Original → SUPPORTED, all mutants → NOT_SUPPORTED.
    script = [json.dumps({"verdict": "supported", "span": ""})]
    # Conservative: up to 5 mutants.
    script += [json.dumps({"verdict": "not_supported", "span": ""}) for _ in range(10)]
    llm = MockLLM(scripted_outputs=script)
    result = MutationProbe(llm).probe(_probe_claim(), _evidence())
    assert result.mutants
    assert result.original_supported is True
    assert result.distinguishable is True
    assert result.resistance == 1.0


def test_probe_not_distinguishable_when_judge_accepts_mutant():
    # Original SUPPORTED, but first mutant also wrongly SUPPORTED.
    script = [
        json.dumps({"verdict": "supported", "span": ""}),
        json.dumps({"verdict": "supported", "span": ""}),  # mutant 1 — leak
        json.dumps({"verdict": "not_supported", "span": ""}),
        json.dumps({"verdict": "not_supported", "span": ""}),
        json.dumps({"verdict": "not_supported", "span": ""}),
        json.dumps({"verdict": "not_supported", "span": ""}),
        json.dumps({"verdict": "not_supported", "span": ""}),
    ]
    llm = MockLLM(scripted_outputs=script)
    result = MutationProbe(llm).probe(_probe_claim(), _evidence())
    assert result.original_supported is True
    assert result.distinguishable is False
    assert result.resistance < 1.0


def test_probe_noop_on_qualitative_claim():
    llm = MockLLM(scripted_outputs=[])
    claim = Claim(text="a purely qualitative description", evidence_ids=["e1"])
    result = MutationProbe(llm).probe(claim, _evidence())
    assert result.mutants == []
    assert result.resistance == 1.0  # trivially resistant
