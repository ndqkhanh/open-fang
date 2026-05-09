from __future__ import annotations

from pathlib import Path

from open_fang.eval.feed import parse_feed, parse_feed_file


def test_parses_markdown_links_to_arxiv():
    md = """
# Agents, 2026 week of April 22

## Memory & RAG
- [BudgetMem: Query-Aware Budget-Tier Routing](https://arxiv.org/abs/2604.10001) — memory routing
- [Learning to Share](https://arxiv.org/abs/2604.10002v2) — selective memory
"""
    entries = parse_feed(md)
    ids = sorted(e.arxiv_id for e in entries)
    assert ids == ["2604.10001", "2604.10002"]
    titles = {e.arxiv_id: e.title for e in entries}
    assert titles["2604.10001"] == "BudgetMem: Query-Aware Budget-Tier Routing"


def test_parses_bare_arxiv_ids_without_markdown_link():
    md = "see arxiv 2604.15034 and also 2604.18292 for recent work"
    entries = parse_feed(md)
    ids = sorted(e.arxiv_id for e in entries)
    assert ids == ["2604.15034", "2604.18292"]


def test_dedupes_duplicate_ids():
    md = """
- [First](https://arxiv.org/abs/2604.05013)
- Also see 2604.05013 in another section
"""
    entries = parse_feed(md)
    assert len(entries) == 1


def test_strips_version_suffix():
    md = "[Paper](https://arxiv.org/abs/2604.05013v3)"
    entries = parse_feed(md)
    assert entries[0].arxiv_id == "2604.05013"


def test_skips_headings_and_empty_lines():
    md = """
# Top heading
## Subheading with https://arxiv.org/abs/2604.99999 in title
- [Body entry](https://arxiv.org/abs/2604.10003)
"""
    entries = parse_feed(md)
    # Heading line (#/##) is skipped; only the list entry counts.
    assert len(entries) == 1
    assert entries[0].arxiv_id == "2604.10003"


def test_parse_feed_file_reads_from_path(tmp_path: Path):
    md = "- [Demo](https://arxiv.org/abs/2604.10004)"
    p = tmp_path / "feed.md"
    p.write_text(md, encoding="utf-8")
    entries = parse_feed_file(p)
    assert entries[0].arxiv_id == "2604.10004"


def test_empty_feed_returns_empty():
    assert parse_feed("") == []
    assert parse_feed("\n\n  \n#   only headings\n") == []
