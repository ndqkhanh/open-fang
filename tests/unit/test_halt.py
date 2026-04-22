from __future__ import annotations

from open_fang.verify.halt import ConfidenceMonitor


def test_halt_requires_full_window():
    mon = ConfidenceMonitor(window=3, threshold=0.85)
    mon.observe("a", True, 0.9)
    mon.observe("b", True, 0.9)
    assert mon.should_halt() is False  # only 2 observations
    mon.observe("c", True, 0.9)
    assert mon.should_halt() is True


def test_halt_fails_on_verdict_flip():
    mon = ConfidenceMonitor(window=3, threshold=0.85)
    mon.observe("a", True, 0.95)
    mon.observe("b", False, 0.95)
    mon.observe("c", True, 0.95)
    assert mon.should_halt() is False


def test_halt_fails_on_low_confidence():
    mon = ConfidenceMonitor(window=3, threshold=0.85)
    mon.observe("a", True, 0.9)
    mon.observe("b", True, 0.5)  # below threshold
    mon.observe("c", True, 0.9)
    assert mon.should_halt() is False


def test_halt_counter_increments():
    mon = ConfidenceMonitor(window=3, threshold=0.85)
    for i in range(5):
        mon.observe(f"c{i}", True, 0.95)
        mon.should_halt()
    # After 5 observations: windows of (0,1,2), (1,2,3), (2,3,4) all halt — 3 halts.
    # But the window starts reporting halt from the 3rd observation onward.
    assert mon.halts_fired >= 3


def test_window_drops_oldest():
    mon = ConfidenceMonitor(window=2, threshold=0.85)
    mon.observe("a", True, 0.9)
    mon.observe("b", False, 0.9)
    mon.observe("c", False, 0.9)  # evicts a, window now [b, c]
    assert mon.should_halt() is True  # both False with high confidence


def test_reset_clears_window():
    mon = ConfidenceMonitor(window=2, threshold=0.85)
    mon.observe("a", True, 0.95)
    mon.observe("b", True, 0.95)
    assert mon.should_halt() is True
    mon.reset()
    assert mon.should_halt() is False


def test_stats_expose_halt_count():
    mon = ConfidenceMonitor(window=2, threshold=0.85)
    mon.observe("a", True, 0.95)
    mon.observe("b", True, 0.95)
    mon.should_halt()
    stats = mon.stats()
    assert stats["halts_fired"] == 1
    assert stats["window"] == 2
    assert stats["threshold"] == 0.85
