from __future__ import annotations

import pytest

from open_fang.skills.schema import SkillParseError, parse_skill_md

_MIN = """---
name: test-skill
description: "a skill for tests"
origin: curated
---

## Overview
overview body

## When to Activate
activate when X

## Concepts
c

## Code Examples
e

## Anti-Patterns
a

## Best Practices
b
"""


def test_parses_minimal_valid_skill():
    skill = parse_skill_md(_MIN)
    assert skill.name == "test-skill"
    assert skill.description == "a skill for tests"
    assert skill.origin == "curated"
    assert skill.overview == "overview body"
    assert skill.when_to_activate == "activate when X"


def test_rejects_missing_frontmatter():
    with pytest.raises(SkillParseError):
        parse_skill_md("## Overview\nbody")


def test_rejects_unclosed_frontmatter():
    with pytest.raises(SkillParseError):
        parse_skill_md("---\nname: x\ndescription: y\norigin: curated\n")


def test_rejects_unknown_origin():
    bad = _MIN.replace("origin: curated", "origin: magic")
    with pytest.raises(SkillParseError):
        parse_skill_md(bad)


def test_rejects_missing_required_key():
    bad = _MIN.replace("description: \"a skill for tests\"\n", "")
    with pytest.raises(SkillParseError):
        parse_skill_md(bad)


def test_learned_origin_requires_confidence():
    bad = _MIN.replace("origin: curated", "origin: learned")
    with pytest.raises(SkillParseError):
        parse_skill_md(bad)


def test_learned_with_confidence_passes():
    good = _MIN.replace(
        "origin: curated",
        "origin: learned\nconfidence: 0.75",
    )
    skill = parse_skill_md(good)
    assert skill.origin == "learned"
    assert skill.frontmatter.confidence == 0.75


def test_confidence_out_of_range_rejected():
    bad = _MIN.replace(
        "origin: curated",
        "origin: learned\nconfidence: 1.5",
    )
    with pytest.raises(SkillParseError):
        parse_skill_md(bad)


def test_confidence_non_numeric_rejected():
    bad = _MIN.replace(
        "origin: curated",
        "origin: learned\nconfidence: medium",
    )
    with pytest.raises(SkillParseError):
        parse_skill_md(bad)
