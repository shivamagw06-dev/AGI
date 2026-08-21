"""The backfill timer lives in memory, so a redeploy must not cost an interval."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_sched_"))

from institutional_warehouse import db, scheduler  # noqa: E402
from institutional_warehouse.backfill import checkpoints  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_warehouse(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    monkeypatch.delenv("WAREHOUSE_BACKFILL", raising=False)
    monkeypatch.setenv("WAREHOUSE_BACKFILL_INTERVAL_MIN", "30")
    # These cover restart timing, not the trading calendar. Without this they
    # pass overnight and fail during market hours, which is the worst kind of
    # test - one whose result depends on when you ran it.
    monkeypatch.setenv("WAREHOUSE_BACKFILL_MARKET_GUARD", "false")
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


def _record_slice(minutes_ago: float) -> None:
    job_id = checkpoints.start_job("backfill", actor="test")
    stamp = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat(timespec="seconds")
    db.execute("UPDATE wh_backfill_jobs SET created_at = ? WHERE id = ?", (stamp, job_id))


def test_age_is_read_from_the_job_table_not_the_process():
    assert scheduler.minutes_since_last_slice() is None
    _record_slice(12)
    age = scheduler.minutes_since_last_slice()
    assert age is not None and 11 <= age <= 13


def test_a_restart_runs_immediately_when_a_slice_is_overdue(monkeypatch):
    _record_slice(51)  # the gap a redeploy actually produced in production
    monkeypatch.setenv("WAREHOUSE_BACKFILL", "true")
    ran = {"count": 0}
    monkeypatch.setattr(scheduler, "_backfill_slice", lambda: ran.__setitem__("count", 1))
    monkeypatch.setattr(scheduler.threading, "Thread", _StubThread)

    result = scheduler.start_backfill()
    assert result["boot_slice"] is True
    assert ran["count"] == 1
    scheduler.stop_backfill()


def test_a_restart_waits_when_a_slice_has_just_run(monkeypatch):
    _record_slice(3)
    monkeypatch.setenv("WAREHOUSE_BACKFILL", "true")
    ran = {"count": 0}
    monkeypatch.setattr(scheduler, "_backfill_slice", lambda: ran.__setitem__("count", 1))
    monkeypatch.setattr(scheduler.threading, "Thread", _StubThread)

    result = scheduler.start_backfill()
    assert result["boot_slice"] is False
    assert ran["count"] == 0          # no double-run right after a completed slice
    scheduler.stop_backfill()


def test_status_reports_loop_health_from_shared_state():
    _record_slice(5)
    healthy = scheduler.backfill_status()
    assert healthy["minutes_since_last_slice"] < 10
    assert healthy["loop_healthy"] is True

    db.execute("DELETE FROM wh_backfill_jobs")
    _record_slice(400)
    stalled = scheduler.backfill_status()
    assert stalled["loop_healthy"] is False


class _StubThread:
    """Keeps the test off real threads while preserving the start/join contract."""

    def __init__(self, *args, **kwargs):
        self._alive = False

    def start(self):
        self._alive = True

    def is_alive(self):
        return self._alive

    def join(self, timeout=None):
        self._alive = False
