"""Holding the backfill off while the exchange is trading.

The desk rebuilds its cache every fifteen minutes. That rebuild takes about
twelve seconds on an idle box; with a backfill slice running it goes past sixty
and the request times out. On 21 August that was happening at 11:48 IST with the
market open and clients on the site.

The repair has all night. The client looking at a screen does not.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from institutional_warehouse import scheduler

IST = timezone(timedelta(hours=5, minutes=30))


def _ist(day: str, hour: int, minute: int = 0) -> datetime:
    return datetime.fromisoformat(f"{day}T{hour:02d}:{minute:02d}:00").replace(tzinfo=IST)


class TestMarketHours:
    # 2026-08-21 is a Friday, 2026-08-22 a Saturday.
    @pytest.mark.parametrize("hour,minute", [(9, 15), (11, 48), (13, 0), (15, 29)])
    def test_trading_hours_are_held(self, hour, minute):
        assert scheduler.within_market_hours(_ist("2026-08-21", hour, minute))

    @pytest.mark.parametrize("hour,minute", [(3, 0), (8, 30), (16, 0), (22, 0)])
    def test_outside_trading_hours_it_runs(self, hour, minute):
        assert not scheduler.within_market_hours(_ist("2026-08-21", hour, minute))

    def test_the_margin_covers_the_pre_open_and_the_close(self):
        """The pre-open session starts at 09:00 and the closing auction runs to
        15:40, and both move prices."""
        assert scheduler.within_market_hours(_ist("2026-08-21", 9, 5))
        assert scheduler.within_market_hours(_ist("2026-08-21", 15, 40))

    def test_the_weekend_is_free(self):
        """The exchange is shut, so the repair gets two clear days."""
        assert not scheduler.within_market_hours(_ist("2026-08-22", 11, 48))
        assert not scheduler.within_market_hours(_ist("2026-08-23", 11, 48))

    def test_the_guard_can_be_turned_off(self, monkeypatch):
        """For a deliberate catch-up when nobody is watching the screens."""
        monkeypatch.setenv("WAREHOUSE_BACKFILL_MARKET_GUARD", "false")
        assert not scheduler.within_market_hours(_ist("2026-08-21", 11, 48))

    def test_a_slice_asked_for_during_trading_declines(self, monkeypatch):
        monkeypatch.setattr(scheduler, "within_market_hours", lambda *a, **k: True)
        assert scheduler._backfill_slice() == {"ok": True, "skipped": "market_hours"}

    def test_the_boot_slice_also_waits(self, monkeypatch):
        """A redeploy during trading hours must not start one immediately."""
        monkeypatch.setenv("WAREHOUSE_BACKFILL", "true")
        monkeypatch.setattr(scheduler, "within_market_hours", lambda *a, **k: True)
        monkeypatch.setattr(scheduler, "minutes_since_last_slice", lambda: 999.0)
        ran = []
        monkeypatch.setattr(scheduler, "_backfill_slice", lambda: ran.append(1))
        out = scheduler.start_backfill()
        scheduler.stop_backfill()
        assert out.get("boot_slice") is False
        assert ran == []
