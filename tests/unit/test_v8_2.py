from __future__ import annotations

from open_fang.kb.entities import (
    canonicalize,
    extract_affiliations,
    extract_all,
    extract_authors,
    extract_benchmarks,
    extract_techniques,
)


def test_canonicalize_basic():
    assert canonicalize("Univeristy of Michigan") == "univeristy of michigan"
    assert canonicalize("  MIT!  ") == "mit"


def test_extract_techniques_finds_seeded():
    techs = extract_techniques("This paper builds on ReWOO and compares against ReAct.")
    kinds = {e.canonical for e in techs}
    assert "rewoo" in kinds
    assert "react" in kinds


def test_extract_techniques_case_insensitive():
    techs = extract_techniques("rewoo and REACT are both interesting.")
    assert len(techs) >= 2


def test_extract_techniques_deduplicates():
    techs = extract_techniques("ReWOO ReWOO ReWOO is mentioned three times.")
    canonicals = [e.canonical for e in techs]
    assert canonicals.count("rewoo") == 1


def test_extract_benchmarks():
    benchs = extract_benchmarks("We evaluate on SWE-bench and GAIA benchmarks.")
    kinds = {e.canonical for e in benchs}
    assert any("swe" in k for k in kinds)
    assert "gaia" in kinds


def test_extract_affiliations():
    aff = extract_affiliations("Researchers from MIT and Anthropic collaborated.")
    names = {e.canonical for e in aff}
    assert "mit" in names
    assert "anthropic" in names


def test_extract_authors_csv():
    out = extract_authors("Alice, Bob, Charlie")
    assert [e.name for e in out] == ["Alice", "Bob", "Charlie"]


def test_extract_authors_dedupe():
    out = extract_authors("Alice, Bob, alice")
    # 'Alice' and 'alice' canonicalize to same key.
    assert len(out) == 2


def test_extract_all_integrates_all_kinds():
    entities, edges = extract_all(
        "arxiv:x",
        content="ReWOO was developed at MIT and evaluated on SWE-bench.",
        authors_csv="Smith, Jones",
    )
    kinds = {e.kind for e in entities}
    assert kinds == {"author", "affiliation", "technique", "benchmark"}

    link_kinds = {e.link_kind for e in edges}
    assert link_kinds == {
        "authored_by", "affiliated_with", "uses_technique", "evaluates_on",
    }
    assert all(e.src_paper_id == "arxiv:x" for e in edges)


def test_extra_technique_names_accepted():
    techs = extract_techniques(
        "FancyNewMethod works great.", extra=("FancyNewMethod",)
    )
    assert any(e.canonical == "fancynewmethod" for e in techs)


def test_empty_content_returns_empty():
    entities, edges = extract_all("arxiv:x", content="", authors_csv="")
    assert entities == []
    assert edges == []
