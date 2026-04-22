"""Awesome-list feed parser — extract arxiv IDs + titles from a markdown file.

Per v2-plan.md §CC-1. Live network pulls are out of scope for v2.7 (they
require HTTP + cache + cron); the parser is the unit that any scheduler
invokes. Feed content is expected to arrive as a local file or via WebFetch
in downstream tooling.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_ENTRY_RE = re.compile(
    # Match either:
    #   - [Title](https://arxiv.org/abs/2604.05013)
    #   - [2604.05013](...) — title ...
    #   - ... 2604.05013 ...
    r"(?:"
    r"\[(?P<title_md>[^\]]+)\]\(https?://arxiv\.org/abs/(?P<arxiv_a>\d{4}\.\d{4,5})(?:v\d+)?\)"
    r"|"
    r"arxiv(?:\.org/abs)?[/:]\s*(?P<arxiv_b>\d{4}\.\d{4,5})(?:v\d+)?"
    r"|"
    r"\b(?P<arxiv_c>\d{4}\.\d{4,5})(?:v\d+)?\b"
    r")",
    re.IGNORECASE,
)


@dataclass
class FeedEntry:
    arxiv_id: str
    title: str
    raw_line: str


def parse_feed(markdown: str) -> list[FeedEntry]:
    """Return one entry per distinct arxiv id found in the markdown."""
    seen: set[str] = set()
    out: list[FeedEntry] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for m in _ENTRY_RE.finditer(stripped):
            aid = m.group("arxiv_a") or m.group("arxiv_b") or m.group("arxiv_c")
            if not aid or aid in seen:
                continue
            seen.add(aid)
            title = (m.group("title_md") or "").strip() or stripped
            out.append(
                FeedEntry(
                    arxiv_id=aid,
                    title=title[:200],
                    raw_line=stripped[:300],
                )
            )
    return out


def parse_feed_file(path: Path | str) -> list[FeedEntry]:
    return parse_feed(Path(path).read_text(encoding="utf-8"))
