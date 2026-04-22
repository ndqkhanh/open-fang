from __future__ import annotations

from pathlib import Path

import pytest

from open_fang.skills.loader import SkillLoader
from open_fang.skills.schema import Skill, SkillFrontmatter
from open_fang.skills.tree import (
    MAX_LEAVES_PER_CATEGORY,
    SkillTreeError,
    build_tree,
    children,
    describe,
    leaves_under,
    navigate,
)


def _skill(name: str, path: Path | None = None) -> Skill:
    return Skill(
        frontmatter=SkillFrontmatter(
            name=name,
            description=f"desc for {name}",
            origin="curated",
        ),
        path=path,
    )


def test_flat_list_becomes_root_children():
    tree = build_tree([_skill("alpha"), _skill("beta")])
    assert children(tree) == ["alpha", "beta"]
    assert navigate(tree, "alpha").skill.name == "alpha"
    assert navigate(tree, "nonexistent") is None


def test_hierarchy_derived_from_path(tmp_path: Path):
    skills_root = tmp_path / "skills"
    skills = [
        _skill("mutation", skills_root / "verify" / "mutation" / "SKILL.md"),
        _skill("executable", skills_root / "verify" / "executable" / "SKILL.md"),
        _skill("survey", skills_root / "retrieve" / "survey" / "SKILL.md"),
    ]
    tree = build_tree(skills, skills_root=skills_root)
    assert children(tree) == ["retrieve", "verify"]
    assert children(tree, "verify") == ["executable", "mutation"]
    node = navigate(tree, "verify/mutation")
    assert node and node.skill.name == "mutation"


def test_leaves_under_collects_all_subtree_skills(tmp_path: Path):
    skills_root = tmp_path / "skills"
    skills = [
        _skill("mutation", skills_root / "verify" / "mutation" / "SKILL.md"),
        _skill("executable", skills_root / "verify" / "executable" / "SKILL.md"),
        _skill("survey", skills_root / "retrieve" / "survey" / "SKILL.md"),
    ]
    tree = build_tree(skills, skills_root=skills_root)
    under_verify = leaves_under(tree, "verify")
    assert sorted(s.name for s in under_verify) == ["executable", "mutation"]
    assert len(leaves_under(tree)) == 3  # all


def test_describe_emits_expected_shape():
    tree = build_tree([_skill("x")])
    root_desc = describe(tree)
    assert root_desc["children"] == ["x"]
    assert root_desc["leaf_count"] == 1
    leaf_desc = describe(tree, "x")
    assert leaf_desc["is_leaf"] is True
    assert leaf_desc["skill"] == "x"


def test_tree_rejects_excess_children():
    """Max 12 leaves per category — a 13th triggers SkillTreeError."""
    skills = [_skill(f"s{i:02d}") for i in range(MAX_LEAVES_PER_CATEGORY + 1)]
    with pytest.raises(SkillTreeError):
        build_tree(skills)


def test_tree_rejects_excess_depth(tmp_path: Path):
    skills_root = tmp_path / "skills"
    very_deep = skills_root / "a" / "b" / "c" / "d" / "deep" / "SKILL.md"
    skill = _skill("deep", very_deep)
    with pytest.raises(SkillTreeError):
        build_tree([skill], skills_root=skills_root)


def test_curated_repo_skills_build_a_valid_flat_tree():
    """The shipped 5 curated skills live in flat folders today — tree handles that."""
    loader = SkillLoader()
    loaded = loader.load()
    tree = build_tree(loaded.skills)
    assert sorted(children(tree)) == sorted(s.name for s in loaded.skills)
    assert len(leaves_under(tree)) == 5
