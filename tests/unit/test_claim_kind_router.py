from __future__ import annotations

from open_fang.models import Claim
from open_fang.verify.router import classify, tiers_for_claim


def _claim(text: str) -> Claim:
    return Claim(text=text, evidence_ids=["e1"])


def test_classify_quantitative_on_percentage():
    c = classify(_claim("ReWOO reduces tokens by 47%"))
    assert c.kind == "quantitative"


def test_classify_quantitative_on_fivefold():
    assert classify(_claim("ReWOO reduces tokens fivefold")).kind == "quantitative"


def test_classify_quantitative_on_comparison_verb():
    assert classify(_claim("Method A outperforms method B")).kind == "quantitative"


def test_classify_methodological_on_experiment_setup():
    c = classify(_claim("The experiment uses a train/test split with 80/20 ratio"))
    # Has both numeric (80/20) and methodology tokens — quant wins per precedence.
    assert c.kind == "quantitative"


def test_classify_pure_methodological():
    c = classify(_claim("The reproducibility protocol requires three independent runs"))
    assert c.kind == "methodological"


def test_classify_citation():
    c = classify(_claim("According to Xu et al., the framework converges"))
    assert c.kind == "citation"


def test_classify_qualitative():
    c = classify(_claim("ReWOO decouples reasoning from observations"))
    assert c.kind == "qualitative"


def test_tiers_for_quantitative_includes_executable():
    tiers = tiers_for_claim(_claim("The system improves by 50%"))
    assert "executable" in tiers
    assert "mutation" in tiers


def test_tiers_for_qualitative_skip_executable_and_mutation():
    tiers = tiers_for_claim(_claim("The architecture is elegant and novel"))
    assert "executable" not in tiers
    assert "mutation" not in tiers
    assert "llm_judge" in tiers


def test_tiers_for_methodological_includes_mutation_but_not_executable():
    tiers = tiers_for_claim(_claim("The methodology follows the reproducibility protocol"))
    assert "mutation" in tiers
    assert "executable" not in tiers


def test_ambiguous_empty_claim_runs_full_pipeline():
    tiers = tiers_for_claim(_claim(""))
    assert "executable" in tiers
    assert "mutation" in tiers
    assert "critic" in tiers
