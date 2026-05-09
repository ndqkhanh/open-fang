"""SkillRegistry: in-memory index of loaded skills with natural-language activation.

v2.0 activation is intentionally simple — token-overlap with the skill's
`When to Activate` section plus its description. v2.1 upgrades to LLM-judged
activation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .loader import SkillLoader
from .schema import Skill

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for",
    "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those", "with", "by", "as", "at",
    "we", "our", "it", "its", "what", "how", "does", "do", "why",
}


def _tokens(text: str) -> set[str]:
    return {
        t.strip(".,;:!?\"'()[]*`").lower()
        for t in text.split()
        if len(t.strip(".,;:!?\"'()[]*`")) > 3
        and t.strip(".,;:!?\"'()[]*`").lower() not in _STOPWORDS
    }


@dataclass
class SkillRegistry:
    skills: list[Skill] = field(default_factory=list)

    @classmethod
    def from_loader(cls, loader: SkillLoader) -> SkillRegistry:
        return cls(skills=loader.load().skills)

    def list(self) -> list[Skill]:  # noqa: A003 - matches CLI verb
        return list(self.skills)

    def get(self, name: str) -> Skill | None:
        for skill in self.skills:
            if skill.name == name:
                return skill
        return None

    def activate(self, query: str, *, max_results: int = 3) -> list[Skill]:
        """Return skills whose activation text overlaps the query, ranked by score."""
        q_tokens = _tokens(query)
        if not q_tokens:
            return []
        scored: list[tuple[float, Skill]] = []
        for skill in self.skills:
            activation_text = " ".join(
                [
                    skill.description,
                    skill.when_to_activate,
                    skill.overview,
                ]
            )
            s_tokens = _tokens(activation_text)
            if not s_tokens:
                continue
            overlap = q_tokens & s_tokens
            if not overlap:
                continue
            score = len(overlap) / max(1, len(q_tokens))
            scored.append((score, skill))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [skill for _, skill in scored[:max_results]]
