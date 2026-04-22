"""v3.0 — agentskills.io alignment tests.

Ensures OpenFang's SKILL.md parser round-trips with the canonical
https://agentskills.io/specification schema.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from open_fang.skills.schema import (
    Skill,
    SkillFrontmatter,
    SkillParseError,
    parse_skill_md,
    validate_skill,
)

_SPEC_MINIMAL = """---
name: pdf-processing
description: "Extract PDF text, fill forms, merge files. Use when handling PDFs."
origin: curated
---
"""

_SPEC_WITH_METADATA = """---
name: pdf-processing
description: "Extract PDF text, fill forms, merge files."
license: Apache-2.0
compatibility: "Requires Python 3.11 and uv"
allowed-tools: "Bash(git:*) Bash(jq:*) Read"
metadata:
  origin: curated
  author: example-org
  version: "1.0"
---
"""

_SPEC_LEARNED_WITH_METADATA_CONFIDENCE = """---
name: citation-extraction-composite
description: "Composite learned from successful trajectories."
metadata:
  origin: learned
  confidence: 0.87
---
"""


def test_spec_minimal_parses():
    skill = parse_skill_md(_SPEC_MINIMAL)
    assert skill.name == "pdf-processing"
    assert "PDF" in skill.description
    assert skill.origin == "curated"
    assert validate_skill(skill) == []


def test_spec_with_metadata_block_parses_and_validates():
    skill = parse_skill_md(_SPEC_WITH_METADATA)
    assert skill.frontmatter.license == "Apache-2.0"
    assert skill.frontmatter.compatibility == "Requires Python 3.11 and uv"
    assert skill.frontmatter.allowed_tools == "Bash(git:*) Bash(jq:*) Read"
    # Origin resolved from metadata.origin.
    assert skill.origin == "curated"
    # Other metadata entries preserved as-is.
    assert skill.frontmatter.metadata["author"] == "example-org"
    assert skill.frontmatter.metadata["version"] == "1.0"
    assert validate_skill(skill) == []


def test_learned_origin_in_metadata_with_confidence():
    skill = parse_skill_md(_SPEC_LEARNED_WITH_METADATA_CONFIDENCE)
    assert skill.origin == "learned"
    assert skill.frontmatter.confidence == pytest.approx(0.87)


def test_learned_origin_in_metadata_without_confidence_rejected():
    bad = _SPEC_LEARNED_WITH_METADATA_CONFIDENCE.replace(
        "confidence: 0.87\n", ""
    )
    with pytest.raises(SkillParseError):
        parse_skill_md(bad)


def test_strict_name_rejects_uppercase():
    skill = Skill(
        frontmatter=SkillFrontmatter(
            name="PDF-Processing",
            description="x",
            origin="curated",
        )
    )
    issues = validate_skill(skill)
    assert any("match" in i for i in issues)


def test_strict_name_rejects_consecutive_hyphens():
    skill = Skill(
        frontmatter=SkillFrontmatter(
            name="pdf--processing",
            description="x",
            origin="curated",
        )
    )
    assert any("match" in i for i in validate_skill(skill))


def test_strict_name_rejects_leading_hyphen():
    skill = Skill(
        frontmatter=SkillFrontmatter(
            name="-leading",
            description="x",
            origin="curated",
        )
    )
    assert any("match" in i for i in validate_skill(skill))


def test_description_length_cap():
    skill = Skill(
        frontmatter=SkillFrontmatter(
            name="x",
            description="y" * 1025,
            origin="curated",
        )
    )
    issues = validate_skill(skill)
    assert any("description exceeds" in i for i in issues)


def test_name_length_cap():
    long = "a" * 65
    skill = Skill(
        frontmatter=SkillFrontmatter(
            name=long,
            description="y",
            origin="curated",
        )
    )
    issues = validate_skill(skill)
    assert any("name exceeds" in i for i in issues)


def test_compatibility_length_cap():
    skill = Skill(
        frontmatter=SkillFrontmatter(
            name="x",
            description="y",
            origin="curated",
            compatibility="c" * 501,
        )
    )
    assert any("compatibility exceeds" in i for i in validate_skill(skill))


def test_folder_name_mismatch_flagged(tmp_path: Path):
    path = tmp_path / "wrong-folder" / "SKILL.md"
    skill = Skill(
        frontmatter=SkillFrontmatter(
            name="pdf-processing",
            description="x",
            origin="curated",
        ),
        path=path,
    )
    issues = validate_skill(skill)
    assert any("parent directory" in i for i in issues)


def test_to_agentskills_yaml_roundtrip_preserves_origin():
    skill = parse_skill_md(_SPEC_WITH_METADATA)
    yaml = skill.to_agentskills_yaml()
    assert "---" in yaml
    assert "name: pdf-processing" in yaml
    assert "license: Apache-2.0" in yaml
    assert "origin: curated" in yaml  # now inside metadata block


def test_to_agentskills_yaml_confidence_in_metadata():
    skill = parse_skill_md(_SPEC_LEARNED_WITH_METADATA_CONFIDENCE)
    yaml = skill.to_agentskills_yaml()
    assert "origin: learned" in yaml
    assert "confidence: 0.87" in yaml


def test_existing_curated_skills_still_validate():
    """All 5 v2.0 curated skills parse and pass validation under the new schema."""
    from open_fang.skills.loader import SkillLoader

    loaded = SkillLoader().load()
    assert loaded.errors == []
    assert len(loaded.skills) == 5
    for skill in loaded.skills:
        # They must all pass validation (name, description, folder match).
        issues = validate_skill(skill)
        assert issues == [], f"{skill.name}: {issues}"


def test_v2_top_level_origin_still_parses():
    """Back-compat: SKILL.md with top-level `origin:` (v2.0 shape) still parses."""
    v2_text = """---
name: legacy-skill
description: "legacy v2 format with top-level origin"
origin: curated
---
"""
    skill = parse_skill_md(v2_text)
    assert skill.origin == "curated"
    assert skill.frontmatter.metadata == {}
