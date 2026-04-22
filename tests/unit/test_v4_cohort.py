"""v4.0 — 9-specialist cohort tests."""
from __future__ import annotations

from open_fang.supervisor.registry import default_supervisor
from open_fang.supervisor.specialist import (
    ClaimVerifierAgent,
    CriticAgent,
    DeepReadAgent,
    MethodologistAgent,
    PublisherAgent,
    ResearchDirectorAgent,
    SurveyAgent,
    SynthesisAgent,
    ThreatModelerAgent,
)

EXPECTED_NAMES = {
    "research-director", "survey", "deep-read", "claim-verifier",
    "methodologist", "synthesis", "critic", "threat-modeler", "publisher",
}
EXPECTED_STAGES = {
    "plan", "retrieve", "extract", "verify", "synthesize",
    "critique", "publish",
}


def test_v4_cohort_has_9_specialists():
    sv = default_supervisor()
    names = {sp.name for sp in sv.specialists}
    assert names == EXPECTED_NAMES


def test_v4_cohort_covers_all_7_stages():
    sv = default_supervisor()
    stages = {sp.stage for sp in sv.specialists}
    assert stages == EXPECTED_STAGES


def test_every_specialist_emits_valid_spec():
    sv = default_supervisor()
    for sp in sv.specialists:
        spec = sp.spec()
        assert spec["name"]
        assert spec["stage"] in EXPECTED_STAGES
        assert isinstance(spec["handles"], list)
        assert isinstance(spec["owned_skills"], list)
        assert isinstance(spec["verifier_tiers"], list) and spec["verifier_tiers"]
        assert spec["model_family_preference"] in {"anthropic", "openai", "either"}


def test_survey_and_deep_read_still_cover_search_and_extract():
    """v3.2 specialists' contracts preserved."""
    assert SurveyAgent.handles == {
        "search.arxiv", "search.semantic_scholar", "search.github"
    }
    assert DeepReadAgent.handles == {"fetch.pdf", "parse.latex", "extract.claims"}


def test_claim_verifier_declares_all_five_tiers():
    assert set(ClaimVerifierAgent.verifier_tiers) == {
        "lexical", "mutation", "llm_judge", "executable", "critic"
    }


def test_methodologist_prefers_executable_tier():
    assert "executable" in MethodologistAgent.verifier_tiers


def test_critic_prefers_openai_family():
    """Cross-family second opinion: critic runs a different model family."""
    assert CriticAgent.model_family_preference == "openai"


def test_research_director_has_budget_ceiling():
    """Orchestrator roles should carry a cost cap."""
    assert ResearchDirectorAgent.cost_ceiling_usd > 0


def test_publisher_has_tight_budget():
    assert PublisherAgent.cost_ceiling_usd > 0


def test_threat_modeler_runs_critic_tier():
    assert "critic" in ThreatModelerAgent.verifier_tiers


def test_synthesis_prefers_anthropic():
    assert SynthesisAgent.model_family_preference == "anthropic"
