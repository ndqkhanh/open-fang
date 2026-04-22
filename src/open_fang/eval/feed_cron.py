"""FeedCron (v5.4) — opt-in weekly puller for the awesome-list.

Pulls the awesome-list markdown → parses arxiv IDs → imports new papers
into the KB. Hard cap per run (20 by default) prevents runaway imports.

Activation via env:
    OPEN_FANG_FEED_CRON=1                   enable at pipeline startup
    OPEN_FANG_FEED_INTERVAL_HOURS=168        default 168 (weekly)
    OPEN_FANG_FEED_URL=<markdown url>        override default feed source
    OPEN_FANG_FEED_MAX_IMPORTS=20            per-tick cap

The cron uses a thread + sleep loop (no OS-level cron). Call `stop()` to
shut down cleanly.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from ..kb.store import KBStore
from ..models import SourceRef
from .feed import parse_feed

DEFAULT_INTERVAL_HOURS = 168
DEFAULT_MAX_IMPORTS = 20


@dataclass
class FeedCronStats:
    ticks_run: int = 0
    entries_scanned: int = 0
    papers_imported: int = 0
    errors: list[str] = field(default_factory=list)


class FeedCron:
    """Thread-based cron. Callers supply a `feed_provider` that returns the
    raw markdown; in production this is a WebFetch wrapper, in tests a stub."""

    def __init__(
        self,
        *,
        kb: KBStore,
        feed_provider: Callable[[], str],
        interval_hours: float = DEFAULT_INTERVAL_HOURS,
        max_imports_per_tick: int = DEFAULT_MAX_IMPORTS,
        clock: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.kb = kb
        self.feed_provider = feed_provider
        self.interval_seconds = interval_hours * 3600.0
        self.max_imports = max_imports_per_tick
        self.clock = clock
        self.sleep_fn = sleep_fn
        self.stats = FeedCronStats()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def tick(self) -> int:
        """Run a single pull+import cycle. Returns count of new imports."""
        self.stats.ticks_run += 1
        try:
            markdown = self.feed_provider()
        except Exception as exc:  # noqa: BLE001
            self.stats.errors.append(f"feed_provider: {type(exc).__name__}: {exc}")
            return 0

        entries = parse_feed(markdown)
        self.stats.entries_scanned += len(entries)
        existing = set(self.kb.list_paper_ids())
        imported = 0
        for entry in entries:
            paper_id = f"arxiv:{entry.arxiv_id}"
            if paper_id in existing:
                continue
            try:
                self.kb.upsert_paper(
                    SourceRef(kind="arxiv", identifier=paper_id, title=entry.title),
                    abstract=f"Imported via feed_cron at {self.stats.ticks_run}th tick.",
                )
                imported += 1
                existing.add(paper_id)
            except Exception as exc:  # noqa: BLE001
                self.stats.errors.append(f"upsert {paper_id}: {exc}")
            if imported >= self.max_imports:
                break
        self.stats.papers_imported += imported
        return imported

    def start(self) -> None:
        """Start the background tick loop."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self, *, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self.tick()
            # Instead of one long sleep, poll the stop event in small increments
            # so stop() returns quickly.
            remaining = self.interval_seconds
            while remaining > 0 and not self._stop_event.is_set():
                chunk = min(remaining, 1.0)
                self.sleep_fn(chunk)
                remaining -= chunk


def enabled_via_env() -> bool:
    return os.environ.get("OPEN_FANG_FEED_CRON", "").strip() == "1"


def interval_hours_from_env() -> float:
    raw = os.environ.get("OPEN_FANG_FEED_INTERVAL_HOURS", "").strip()
    try:
        return float(raw) if raw else DEFAULT_INTERVAL_HOURS
    except ValueError:
        return DEFAULT_INTERVAL_HOURS


def max_imports_from_env() -> int:
    raw = os.environ.get("OPEN_FANG_FEED_MAX_IMPORTS", "").strip()
    try:
        return int(raw) if raw else DEFAULT_MAX_IMPORTS
    except ValueError:
        return DEFAULT_MAX_IMPORTS
