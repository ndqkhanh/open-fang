"""SkillTree (v5.1) — Navigate-not-retrieve hierarchical skill organization.

Inspired by arxiv:2604.14572 Corpus2Skill. The agent navigates `cd`-style
path segments rather than retrieving-and-ranking against a flat list. At
our skill volume (5-50 skills) either works; at 50+ the hierarchy scales
meaningfully better.

Constraints (per v5-plan.md §W1 risk mitigation):
    max category depth: 3 levels
    max leaves per category: 12

A `SkillLoader` that encounters nested `SKILL.md` files populates the tree
automatically; flat `skills/` become children of root.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .schema import Skill


@dataclass
class SkillTreeNode:
    name: str
    skill: Skill | None = None
    children: dict[str, SkillTreeNode] = field(default_factory=dict)
    path_segments: tuple[str, ...] = ()

    @property
    def is_leaf(self) -> bool:
        return self.skill is not None and not self.children

    @property
    def child_count(self) -> int:
        return len(self.children)


class SkillTreeError(ValueError):
    """Raised when the tree violates depth/leaf caps or contains a cycle."""


MAX_DEPTH = 3
MAX_LEAVES_PER_CATEGORY = 12


def build_tree(
    skills: list[Skill],
    *,
    skills_root: Path | None = None,
) -> SkillTreeNode:
    """Assemble a hierarchical tree from a flat skill list.

    If `skills_root` is given, derive hierarchy from skill paths relative to
    that root (so `skills/verify/mutation/SKILL.md` becomes `verify/mutation`).
    Otherwise all skills are direct children of the root.
    """
    root = SkillTreeNode(name="/")
    for skill in skills:
        segments = _segments_for(skill, skills_root)
        if len(segments) > MAX_DEPTH + 1:
            raise SkillTreeError(
                f"skill {skill.name!r} exceeds max depth {MAX_DEPTH} ({segments})"
            )
        _insert(root, segments, skill)
    _validate_leaf_counts(root)
    return root


def navigate(root: SkillTreeNode, path: str) -> SkillTreeNode | None:
    """Traverse `a/b/c` path segments from root. Returns None if missing."""
    current = root
    for segment in _path_segments(path):
        child = current.children.get(segment)
        if child is None:
            return None
        current = child
    return current


def children(root: SkillTreeNode, path: str = "") -> list[str]:
    """Return the direct children's names at the given path."""
    node = navigate(root, path) if path else root
    if node is None:
        return []
    return sorted(node.children.keys())


def leaves_under(root: SkillTreeNode, path: str = "") -> list[Skill]:
    """Collect every skill under a path (DFS)."""
    node = navigate(root, path) if path else root
    if node is None:
        return []
    out: list[Skill] = []
    _collect_leaves(node, out)
    return out


def describe(root: SkillTreeNode, path: str = "") -> dict:
    """Return a JSON-friendly description of the subtree at `path`."""
    node = navigate(root, path) if path else root
    if node is None:
        return {}
    return {
        "name": node.name,
        "path": "/".join(node.path_segments) if node.path_segments else "",
        "is_leaf": node.is_leaf,
        "skill": node.skill.name if node.skill else None,
        "children": sorted(node.children.keys()),
        "leaf_count": sum(1 for _ in _iter_leaves(node)),
    }


def _segments_for(skill: Skill, skills_root: Path | None) -> list[str]:
    if skills_root is None or skill.path is None:
        return [skill.name]
    try:
        relative = skill.path.parent.relative_to(skills_root)
    except ValueError:
        return [skill.name]
    segments = [p for p in relative.parts if p]
    return segments or [skill.name]


def _insert(root: SkillTreeNode, segments: list[str], skill: Skill) -> None:
    current = root
    path_so_far: list[str] = []
    for segment in segments[:-1]:
        path_so_far.append(segment)
        if segment not in current.children:
            current.children[segment] = SkillTreeNode(
                name=segment,
                path_segments=tuple(path_so_far),
            )
        current = current.children[segment]
    leaf_name = segments[-1]
    path_so_far.append(leaf_name)
    current.children[leaf_name] = SkillTreeNode(
        name=leaf_name,
        skill=skill,
        path_segments=tuple(path_so_far),
    )


def _validate_leaf_counts(node: SkillTreeNode) -> None:
    """Recursively ensure no category has more than MAX_LEAVES_PER_CATEGORY children."""
    if node.child_count > MAX_LEAVES_PER_CATEGORY:
        raise SkillTreeError(
            f"category {node.name!r} has {node.child_count} children "
            f"(max {MAX_LEAVES_PER_CATEGORY})"
        )
    for child in node.children.values():
        _validate_leaf_counts(child)


def _path_segments(path: str) -> list[str]:
    return [p for p in path.replace("\\", "/").strip("/").split("/") if p]


def _collect_leaves(node: SkillTreeNode, out: list[Skill]) -> None:
    if node.skill is not None and node.is_leaf:
        out.append(node.skill)
    for child in node.children.values():
        _collect_leaves(child, out)


def _iter_leaves(node: SkillTreeNode):
    if node.is_leaf and node.skill is not None:
        yield node.skill
    for child in node.children.values():
        yield from _iter_leaves(child)
