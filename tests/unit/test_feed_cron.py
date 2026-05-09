from __future__ import annotations

from open_fang.eval.feed_cron import (
    DEFAULT_INTERVAL_HOURS,
    DEFAULT_MAX_IMPORTS,
    FeedCron,
    enabled_via_env,
    interval_hours_from_env,
    max_imports_from_env,
)
from open_fang.kb.store import KBStore

_FEED_MARKDOWN = """
# Recent
- [BudgetMem](https://arxiv.org/abs/2604.10001) — memory
- [SkillCraft](https://arxiv.org/abs/2604.10002) — skills
- [TraceOps](https://arxiv.org/abs/2604.10003) — tracing
"""


def _kb() -> KBStore:
    return KBStore(db_path=":memory:").open()


def test_tick_imports_new_papers():
    kb = _kb()
    cron = FeedCron(kb=kb, feed_provider=lambda: _FEED_MARKDOWN)
    imported = cron.tick()
    assert imported == 3
    assert cron.stats.ticks_run == 1
    assert cron.stats.papers_imported == 3
    assert kb.count_papers() == 3


def test_tick_is_idempotent():
    kb = _kb()
    cron = FeedCron(kb=kb, feed_provider=lambda: _FEED_MARKDOWN)
    cron.tick()
    second = cron.tick()
    assert second == 0
    assert kb.count_papers() == 3  # deduped


def test_tick_respects_max_imports_cap():
    kb = _kb()
    large_feed = "\n".join(
        f"- [P{i}](https://arxiv.org/abs/2604.{i:05d})" for i in range(100)
    )
    cron = FeedCron(
        kb=kb,
        feed_provider=lambda: large_feed,
        max_imports_per_tick=5,
    )
    imported = cron.tick()
    assert imported == 5
    assert kb.count_papers() == 5


def test_tick_records_feed_provider_errors():
    def _raising() -> str:
        raise RuntimeError("network unreachable")

    cron = FeedCron(kb=_kb(), feed_provider=_raising)
    imported = cron.tick()
    assert imported == 0
    assert len(cron.stats.errors) == 1
    assert "network unreachable" in cron.stats.errors[0]


def test_env_reader_defaults(monkeypatch):
    monkeypatch.delenv("OPEN_FANG_FEED_CRON", raising=False)
    assert enabled_via_env() is False
    monkeypatch.setenv("OPEN_FANG_FEED_CRON", "1")
    assert enabled_via_env() is True

    monkeypatch.delenv("OPEN_FANG_FEED_INTERVAL_HOURS", raising=False)
    assert interval_hours_from_env() == DEFAULT_INTERVAL_HOURS
    monkeypatch.setenv("OPEN_FANG_FEED_INTERVAL_HOURS", "24")
    assert interval_hours_from_env() == 24.0

    monkeypatch.delenv("OPEN_FANG_FEED_MAX_IMPORTS", raising=False)
    assert max_imports_from_env() == DEFAULT_MAX_IMPORTS
    monkeypatch.setenv("OPEN_FANG_FEED_MAX_IMPORTS", "50")
    assert max_imports_from_env() == 50


def test_env_reader_bad_values_fall_back_to_defaults(monkeypatch):
    monkeypatch.setenv("OPEN_FANG_FEED_INTERVAL_HOURS", "not_a_number")
    assert interval_hours_from_env() == DEFAULT_INTERVAL_HOURS
    monkeypatch.setenv("OPEN_FANG_FEED_MAX_IMPORTS", "oops")
    assert max_imports_from_env() == DEFAULT_MAX_IMPORTS
