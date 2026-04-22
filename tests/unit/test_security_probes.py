from __future__ import annotations

from open_fang.models import Evidence, SourceRef
from open_fang.security.probes import (
    AdversarialKBProbe,
    CitationPoisoningProbe,
    InstructionHidingProbe,
    PromptInjectionProbe,
    detect_static_attacks,
)


def _ev() -> Evidence:
    return Evidence(
        source=SourceRef(kind="arxiv", identifier="arxiv:rewoo", title="ReWOO"),
        content="ReWOO decouples reasoning from observations.",
        channel="abstract",
    )


def test_prompt_injection_appends_instructions():
    r = PromptInjectionProbe(template_idx=0).apply(_ev())
    assert r.kind == "prompt-injection"
    assert "Ignore all prior instructions" in r.tampered.content


def test_citation_poisoning_plants_fake_id():
    r = CitationPoisoningProbe(fake_id="arxiv:2999.99999").apply(_ev())
    assert r.kind == "citation-poisoning"
    assert "arxiv:2999.99999" in r.tampered.content


def test_instruction_hiding_adds_hidden_markers():
    r = InstructionHidingProbe().apply(_ev())
    assert r.kind == "instruction-hiding"
    # Zero-width space OR HTML comment should be present.
    assert "​" in r.tampered.content or "<!--" in r.tampered.content


def test_adversarial_kb_yields_fabricated_paper():
    r = AdversarialKBProbe(fake_id="arxiv:3999.00001").apply(_ev())
    assert r.kind == "adversarial-kb"
    assert r.tampered.source.identifier == "arxiv:3999.00001"
    assert r.tampered.source.title != _ev().source.title  # distinct from real source


def test_static_detector_flags_injection():
    tampered = PromptInjectionProbe().apply(_ev()).tampered
    flags = detect_static_attacks(tampered)
    assert "prompt-injection" in flags


def test_static_detector_flags_instruction_hiding():
    tampered = InstructionHidingProbe().apply(_ev()).tampered
    flags = detect_static_attacks(tampered)
    assert "instruction-hiding" in flags


def test_static_detector_is_silent_on_clean_content():
    flags = detect_static_attacks(_ev())
    assert flags == []


def test_probes_do_not_mutate_the_original_evidence():
    original = _ev()
    PromptInjectionProbe().apply(original)
    CitationPoisoningProbe().apply(original)
    InstructionHidingProbe().apply(original)
    assert original.content == "ReWOO decouples reasoning from observations."
