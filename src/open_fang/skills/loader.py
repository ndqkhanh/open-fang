"""SkillLoader: discover SKILL.md files across the four-location resolution hierarchy."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .schema import Skill, SkillParseError, parse_skill_md


def default_search_paths() -> list[Path]:
    """Return the four-location resolution order, in priority order.

    Earlier entries win on name conflicts. Missing directories are silently
    skipped — matching ECC's no-errors-on-missing policy.
    """
    repo_root = _find_repo_root()
    home = Path.home()
    return [
        repo_root / "skills",
        home / ".openfang" / "skills" / "learned",
        home / ".openfang" / "skills" / "imported",
        home / ".openfang" / "skills" / "evolved",
    ]


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    # Walk up until we find a directory containing pyproject.toml (the project root).
    for parent in [here.parent] + list(here.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    # Fallback — use cwd rather than raise; this path is opt-in for tests anyway.
    return Path.cwd()


@dataclass
class LoadResult:
    skills: list[Skill] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)


@dataclass
class SkillLoader:
    """Discover and parse skill files across a list of search paths."""

    search_paths: list[Path] = field(default_factory=default_search_paths)
    min_confidence: float = 0.0  # filter: drop skills below this (learned/evolved only)

    def load(self) -> LoadResult:
        result = LoadResult()
        seen: set[str] = set()
        for root in self.search_paths:
            if not root.exists() or not root.is_dir():
                continue
            for skill_md in sorted(root.glob("*/SKILL.md")):
                try:
                    skill = parse_skill_md(skill_md.read_text(encoding="utf-8"), path=skill_md)
                except SkillParseError as exc:
                    result.errors.append((skill_md, str(exc)))
                    continue
                if skill.name in seen:
                    # Earlier search path wins on name conflict.
                    continue
                if not self._passes_confidence_filter(skill):
                    continue
                seen.add(skill.name)
                result.skills.append(skill)
        return result

    def _passes_confidence_filter(self, skill: Skill) -> bool:
        if skill.origin in {"curated", "imported"}:
            return True
        confidence = skill.frontmatter.confidence
        return confidence is not None and confidence >= self.min_confidence
