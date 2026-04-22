"""SKILL.md schema + parser — aligned with https://agentskills.io (v3.0).

Canonical spec fields:
    name           — required; ^[a-z0-9]+(-[a-z0-9]+)*$; ≤64 chars; matches folder
    description    — required; ≤1024 chars
    license        — optional
    compatibility  — optional; ≤500 chars
    metadata       — optional; arbitrary key/value map
    allowed-tools  — optional; space-separated string (experimental)

OpenFang-specific extensions (v2.0):
    origin         — curated | learned | imported | evolved
    confidence     — 0.0-1.0, required for learned/evolved

Parser accepts both:
    - top-level `origin:` + `confidence:` (v2 shape; back-compat)
    - nested `metadata.origin` + `metadata.confidence` (spec-compliant shape)

Body content has no format restrictions per spec. Our curated skills use six
recommended sections (Overview / When to Activate / Concepts / Code Examples /
Anti-Patterns / Best Practices) — they stay as conventions, not requirements.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

SKILL_ORIGINS = {"curated", "learned", "imported", "evolved"}

SECTION_HEADERS = (
    "Overview",
    "When to Activate",
    "Concepts",
    "Code Examples",
    "Anti-Patterns",
    "Best Practices",
)

_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_NAME_LEN = 64
_MAX_DESCRIPTION_LEN = 1024
_MAX_COMPAT_LEN = 500


class SkillParseError(ValueError):
    """Raised when a SKILL.md can't be parsed or fails schema validation."""


@dataclass
class SkillFrontmatter:
    name: str
    description: str
    origin: Literal["curated", "learned", "imported", "evolved"]
    confidence: float | None = None
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    allowed_tools: str | None = None


@dataclass
class Skill:
    frontmatter: SkillFrontmatter
    overview: str = ""
    when_to_activate: str = ""
    concepts: str = ""
    code_examples: str = ""
    anti_patterns: str = ""
    best_practices: str = ""
    path: Path | None = None
    raw_markdown: str = ""
    extras: dict[str, str] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.frontmatter.name

    @property
    def description(self) -> str:
        return self.frontmatter.description

    @property
    def origin(self) -> str:
        return self.frontmatter.origin

    def to_agentskills_yaml(self) -> str:
        """Render the frontmatter in spec-canonical form (origin/confidence nested under metadata)."""
        fm = self.frontmatter
        lines = ["---", f"name: {fm.name}", f'description: "{fm.description}"']
        if fm.license:
            lines.append(f"license: {fm.license}")
        if fm.compatibility:
            lines.append(f"compatibility: {fm.compatibility}")
        if fm.allowed_tools:
            lines.append(f"allowed-tools: {fm.allowed_tools}")
        # Merge OpenFang-specific fields into the metadata block.
        merged_meta = dict(fm.metadata)
        merged_meta.setdefault("origin", fm.origin)
        if fm.confidence is not None:
            merged_meta.setdefault("confidence", fm.confidence)
        if merged_meta:
            lines.append("metadata:")
            for k, v in merged_meta.items():
                lines.append(f"  {k}: {v}")
        lines.append("---")
        return "\n".join(lines)


_FRONTMATTER_DELIM = "---"
_SECTION_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def parse_skill_md(text: str, *, path: Path | None = None) -> Skill:
    """Parse a SKILL.md document. Raises SkillParseError on malformed input."""
    fm, body = _split_frontmatter(text)
    frontmatter = _parse_frontmatter(fm)
    sections = _extract_sections(body)
    return Skill(
        frontmatter=frontmatter,
        overview=sections.get("Overview", "").strip(),
        when_to_activate=sections.get("When to Activate", "").strip(),
        concepts=sections.get("Concepts", "").strip(),
        code_examples=sections.get("Code Examples", "").strip(),
        anti_patterns=sections.get("Anti-Patterns", "").strip(),
        best_practices=sections.get("Best Practices", "").strip(),
        path=path,
        raw_markdown=text,
        extras={k: v for k, v in sections.items() if k not in SECTION_HEADERS},
    )


def validate_skill(skill: Skill) -> list[str]:
    """Return a list of spec-violation messages (empty when valid)."""
    issues: list[str] = []
    fm = skill.frontmatter
    if not _NAME_RE.match(fm.name):
        issues.append(
            f"name {fm.name!r} must match ^[a-z0-9]+(-[a-z0-9]+)*$ (no consecutive or leading/trailing hyphens)"
        )
    if len(fm.name) > _MAX_NAME_LEN:
        issues.append(f"name exceeds {_MAX_NAME_LEN} chars ({len(fm.name)})")
    if not fm.description:
        issues.append("description must be non-empty")
    if len(fm.description) > _MAX_DESCRIPTION_LEN:
        issues.append(f"description exceeds {_MAX_DESCRIPTION_LEN} chars ({len(fm.description)})")
    if fm.compatibility and len(fm.compatibility) > _MAX_COMPAT_LEN:
        issues.append(f"compatibility exceeds {_MAX_COMPAT_LEN} chars ({len(fm.compatibility)})")
    if skill.path is not None and skill.path.parent.name != fm.name:
        issues.append(
            f"name {fm.name!r} does not match parent directory {skill.path.parent.name!r}"
        )
    return issues


def _split_frontmatter(text: str) -> tuple[str, str]:
    stripped = text.lstrip("﻿")  # tolerate UTF-8 BOM
    if not stripped.startswith(_FRONTMATTER_DELIM):
        raise SkillParseError("SKILL.md must begin with '---' frontmatter delimiter")
    lines = stripped.splitlines()
    closing_idx: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _FRONTMATTER_DELIM:
            closing_idx = i
            break
    if closing_idx is None:
        raise SkillParseError("SKILL.md frontmatter missing closing '---'")
    fm = "\n".join(lines[1:closing_idx])
    body = "\n".join(lines[closing_idx + 1 :])
    return fm, body


def _parse_frontmatter(fm: str) -> SkillFrontmatter:
    """Parse a minimal YAML subset (top-level scalars + one-level nested `metadata:` block)."""
    data: dict[str, str] = {}
    metadata: dict[str, Any] = {}
    i = 0
    lines = fm.splitlines()
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        if not line or line.startswith("#"):
            i += 1
            continue
        if ":" not in line:
            raise SkillParseError(f"frontmatter line missing ':' — {raw!r}")
        key, _, value = line.partition(":")
        key = key.strip()
        value = _unquote(value.strip())
        # `metadata:` with empty value introduces a nested block of indented k/v lines.
        if key == "metadata" and value == "":
            i += 1
            while i < len(lines):
                child = lines[i]
                if not child.strip():
                    i += 1
                    continue
                # Nested entries must be indented.
                if not (child.startswith(" ") or child.startswith("\t")):
                    break
                inner = child.strip()
                if ":" not in inner:
                    raise SkillParseError(f"metadata line missing ':' — {child!r}")
                ck, _, cv = inner.partition(":")
                raw_cv = cv.strip()
                was_quoted = (
                    len(raw_cv) >= 2
                    and raw_cv[0] == raw_cv[-1]
                    and raw_cv[0] in {'"', "'"}
                )
                unquoted = _unquote(raw_cv)
                metadata[ck.strip()] = unquoted if was_quoted else _coerce(unquoted)
                i += 1
            continue
        data[key] = value
        i += 1

    for required in ("name", "description"):
        if required not in data:
            raise SkillParseError(f"frontmatter missing required key: {required!r}")

    # Accept `origin` at top-level OR nested in `metadata.origin`.
    origin_raw = data.get("origin") or metadata.get("origin")
    if origin_raw is None:
        raise SkillParseError("frontmatter missing required 'origin' (either top-level or metadata.origin)")
    origin = str(origin_raw)
    if origin not in SKILL_ORIGINS:
        raise SkillParseError(f"origin must be one of {sorted(SKILL_ORIGINS)}, got {origin!r}")

    confidence_raw = data.get("confidence", metadata.get("confidence"))
    confidence: float | None = None
    if confidence_raw is not None and confidence_raw != "":
        try:
            confidence = float(confidence_raw)
        except (ValueError, TypeError) as exc:
            raise SkillParseError(f"confidence must be a float, got {confidence_raw!r}") from exc
        if not 0.0 <= confidence <= 1.0:
            raise SkillParseError(f"confidence must be in [0.0, 1.0], got {confidence}")

    if origin in {"learned", "evolved"} and confidence is None:
        raise SkillParseError(
            f"origin={origin!r} requires a confidence field (top-level or metadata.confidence)"
        )

    # Scrub the OpenFang-specific keys out of metadata so the dataclass fields
    # are the single source of truth.
    pruned_metadata = {k: v for k, v in metadata.items() if k not in {"origin", "confidence"}}

    return SkillFrontmatter(
        name=data["name"],
        description=data["description"],
        origin=origin,  # type: ignore[arg-type]
        confidence=confidence,
        license=data.get("license"),
        compatibility=data.get("compatibility"),
        metadata=pruned_metadata,
        allowed_tools=data.get("allowed-tools"),
    )


def _extract_sections(body: str) -> dict[str, str]:
    matches = list(_SECTION_HEADER_RE.finditer(body))
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        header = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        out[header] = body[start:end]
    return out


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _coerce(value: str) -> Any:
    """Coerce a YAML scalar string to bool/int/float where obvious; else leave as string."""
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
