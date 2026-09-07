"""A bounded backfill must actually be bounded.

WAREHOUSE_BACKFILL_DAYS=20 never reached the Upstox price stage. Its window
defaulted to EARLIEST, so a slice the scheduler advertised as twenty days
fetched twenty-six years of daily candles for sixty companies - synchronously,
on the boot path, before the timer that would run the next slice existed. One
such slice ran fourteen minutes without finishing, took the sidecar from 201 MB
to 1.7 GB, and meant the scheduler never started at all.

These assert the three things that were each independently untrue.
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
from datetime import date

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="bw_"))

from institutional_warehouse import db, scheduler  # noqa: E402
from institutional_warehouse.backfill import prices_upstox  # noqa: E402
from institutional_warehouse.backfill.sources import upstox_history  # noqa: E402

TODAY = date(2026, 8, 21)


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


# --------------------------------------------------------------------------
# The window
# --------------------------------------------------------------------------

def test_a_twenty_day_run_never_asks_for_the_year_2000():
    """The defect, stated directly."""
    start = prices_upstox.window_start(20, end=TODAY)
    assert start == date(2026, 8, 1)
    assert start != upstox_history.EARLIEST
    assert start.year == 2026


@pytest.mark.parametrize("days", [1, 7, 20, 40, 365])
def test_any_bounded_window_stays_inside_it(days):
    start = prices_upstox.window_start(days, end=TODAY)
    assert (TODAY - start).days == days
    assert start > upstox_history.EARLIEST


def test_the_decade_is_collected_only_when_it_is_asked_for():
    """Deep history is a request now, not what you get by forgetting a window."""
    assert prices_upstox.window_start(20, deep_history=True, end=TODAY) == upstox_history.EARLIEST
    assert prices_upstox.window_start(None, end=TODAY) == upstox_history.EARLIEST
    assert prices_upstox.window_start(0, end=TODAY) == upstox_history.EARLIEST


def test_the_engine_actually_passes_days_to_the_price_stage(monkeypatch):
    """The bug was never in the window function - it was the call that skipped it."""
    from institutional_warehouse.backfill import engine

    seen: dict[str, object] = {}

    def fake_backfill(universe=None, **kwargs):
        seen.update(kwargs)
        return {"ok": True, "kind": "upstox_prices", "rows_written": 0}

    monkeypatch.setattr(engine.prices_upstox, "backfill", fake_backfill)
    monkeypatch.setenv("WAREHOUSE_BACKFILL_ALLOW_HERE", "true")
    engine.run(actor="test", stages=["upstox_prices"], companies=60, days=20)

    assert seen.get("days") == 20, "days must reach the stage that ignored it"
    assert seen.get("deep_history") is False
    assert seen.get("limit") == 60


# --------------------------------------------------------------------------
# The deadline
# --------------------------------------------------------------------------

def test_a_slice_stops_at_its_deadline_instead_of_running_forever(monkeypatch):
    monkeypatch.setattr(prices_upstox, "_companies", lambda: {f"S{i}": f"K{i}" for i in range(50)})
    monkeypatch.setattr(prices_upstox.checkpoints, "pending_entities",
                        lambda *a, **k: [f"S{i}" for i in range(50)])

    def slow(ticker, **kwargs):
        time.sleep(0.05)
        return {"ok": True, "symbol": ticker, "rows": 1, "first": "2026-08-01"}

    monkeypatch.setattr(prices_upstox, "backfill_company", slow)
    out = prices_upstox.backfill(days=20, deadline=time.monotonic() + 0.2)
    assert out["stopped_at_deadline"] is True
    assert out["companies_done"] < 50, "it must not have worked through the whole list"


def test_the_engine_skips_remaining_stages_once_the_budget_is_spent(monkeypatch):
    from institutional_warehouse.backfill import engine

    monkeypatch.setenv("WAREHOUSE_BACKFILL_ALLOW_HERE", "true")
    monkeypatch.setattr(engine.nse_archive, "backfill",
                        lambda **k: (time.sleep(0.3) or {"ok": True}))
    called: list[str] = []
    monkeypatch.setattr(engine.prices_upstox, "backfill",
                        lambda *a, **k: (called.append("upstox") or {"ok": True}))

    engine.run(actor="test", stages=["nse_archive", "upstox_prices"],
               companies=1, days=20, max_seconds=0.1)
    assert called == [], "the second stage must not start after the budget is gone"


# --------------------------------------------------------------------------
# Readiness must not wait for the work
# --------------------------------------------------------------------------

def test_the_scheduler_starts_before_the_first_slice_finishes(monkeypatch):
    """Readiness used to depend on sixty companies of data work completing.

    start_backfill ran the boot slice inline, so a slow slice meant the timer
    that runs every later slice was never created.
    """
    started = threading.Event()
    monkeypatch.setenv("WAREHOUSE_BACKFILL", "true")
    monkeypatch.setenv("WAREHOUSE_BACKFILL_INTERVAL_MIN", "10")

    def slow_slice():
        started.set()
        time.sleep(3.0)
        return {"ok": True}

    monkeypatch.setattr(scheduler, "_backfill_slice", slow_slice)
    monkeypatch.setattr(scheduler, "minutes_since_last_slice", lambda: 999.0)
    monkeypatch.setattr(scheduler, "within_market_hours", lambda: False)

    began = time.monotonic()
    out = scheduler.start_backfill()
    elapsed = time.monotonic() - began
    try:
        assert out["enabled"] is True
        assert elapsed < 1.0, f"start_backfill blocked for {elapsed:.2f}s on the slice"
        assert started.wait(timeout=3.0), "the slice must still run, just not in front"
    finally:
        scheduler.stop_backfill()
