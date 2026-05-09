"""OpenFang skill library — ECC-shaped SKILL.md per folder.

v2.0 MVP: parser + loader + registry + 5 curated research skills.
v2.1 adds trajectory-driven extractor + evolving arena.

Resolution order (match ECC):
    1. <repo>/skills/                       — curated, shipped in repo
    2. ~/.openfang/skills/learned/          — extracted from trajectory traces
    3. ~/.openfang/skills/imported/         — third-party
    4. ~/.openfang/skills/evolved/          — from the evolving arena
"""
from .arena import ArenaReport, EvolvingArena
from .diagnostician import Diagnostician, DiagnosticReport, Weakness
from .extractor import ExtractedSkill, TrajectoryExtractor
from .loader import SkillLoader, default_search_paths
from .registry import SkillRegistry
from .schema import Skill, SkillFrontmatter, parse_skill_md

__all__ = [
    "ArenaReport",
    "DiagnosticReport",
    "Diagnostician",
    "EvolvingArena",
    "ExtractedSkill",
    "Skill",
    "SkillFrontmatter",
    "SkillLoader",
    "SkillRegistry",
    "TrajectoryExtractor",
    "Weakness",
    "default_search_paths",
    "parse_skill_md",
]
