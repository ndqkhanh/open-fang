from __future__ import annotations

from pathlib import Path

from open_fang.skills.loader import SkillLoader
from open_fang.skills.registry import SkillRegistry
from open_fang.skills.schema import Skill, SkillFrontmatter


def _skill(name: str, desc: str, activate: str = "") -> Skill:
    return Skill(
        frontmatter=SkillFrontmatter(name=name, description=desc, origin="curated"),
        overview=desc,
        when_to_activate=activate,
    )


def test_list_and_get():
    reg = SkillRegistry(skills=[_skill("a", "apples"), _skill("b", "bananas")])
    names = [s.name for s in reg.list()]
    assert names == ["a", "b"]
    assert reg.get("a").description == "apples"
    assert reg.get("missing") is None


def test_activate_ranks_by_overlap():
    reg = SkillRegistry(
        skills=[
            _skill("citation-extraction", "extract the reference list from a paper"),
            _skill("claim-localization", "find the sentence supporting a claim"),
            _skill("unrelated", "pandas and bamboo populations"),
        ]
    )
    hits = reg.activate("extract citation reference list", max_results=2)
    assert hits[0].name == "citation-extraction"
    assert "unrelated" not in [s.name for s in hits]


def test_activate_returns_empty_on_no_overlap():
    reg = SkillRegistry(skills=[_skill("x", "pandas and bamboo")])
    assert reg.activate("quantum mechanics spectroscopy") == []


def test_registry_consumes_repo_skills():
    """Smoke: the registry initializes with the 5 curated skills from disk."""
    reg = SkillRegistry.from_loader(SkillLoader())
    assert len(reg.list()) == 5
    assert reg.get("claim-localization") is not None


def test_activate_on_real_query(tmp_path: Path):
    """With real skill content, a research-query selects the relevant skill."""
    reg = SkillRegistry.from_loader(SkillLoader())
    hits = reg.activate("extract references from the paper body")
    assert hits
    assert hits[0].name == "citation-extraction"
