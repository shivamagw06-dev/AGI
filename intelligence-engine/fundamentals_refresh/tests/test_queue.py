"""The refresh queue, tested on the things that lose work.

Durable from the first line because today already showed why: a twenty-minute
sweep was killed by a deploy and lost everything, having kept its progress in
the request.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_frq_"))

from fundamentals_refresh import queue as q  # noqa: E402
from institutional_warehouse import db, gateway, store  # noqa: E402


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


def _rows():
    return store.all_rows(q.TAB, limit=100)


class TestEnqueue:
    def test_a_company_and_period_is_queued_once(self):
        q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])
        assert len(_rows()) == 1
        assert _rows()[0]["status"] == q.PENDING

    def test_the_same_event_arriving_twice_does_not_duplicate(self):
        """A feed replaying, or a reconciliation pass overlapping the detector."""
        q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])
        out = q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])
        assert len(_rows()) == 1
        assert out["queued"] == 1

    def test_two_different_periods_are_two_entries(self):
        q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"},
                   {"symbol": "AAA", "reporting_period": "Q2FY27"}])
        assert len(_rows()) == 2

    def test_a_completed_period_is_not_queued_again(self):
        """Re-reporting the same quarter is not a reason to fetch it again."""
        q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])
        q.finish("AAA", "Q1FY27", ok=True)
        out = q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])
        assert out["skipped"] == 1
        assert _rows()[0]["status"] == q.SUCCESS

    def test_the_trigger_is_recorded(self):
        """A queue nobody can explain is one nobody will trust enough to drain."""
        q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}],
                  trigger=q.TRIGGER_RECONCILIATION)
        assert _rows()[0]["trigger"] == q.TRIGGER_RECONCILIATION


class TestClaiming:
    def test_claiming_marks_running_before_the_work_starts(self):
        """A process that dies mid-refresh should leave evidence, not an entry
        that looks untouched to every worker that follows."""
        q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])
        taken = q.claim(limit=5)
        assert [t["symbol"] for t in taken] == ["AAA"]
        assert _rows()[0]["status"] == q.RUNNING

    def test_a_running_entry_is_not_claimed_twice(self):
        q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])
        q.claim(limit=5)
        assert q.claim(limit=5) == []

    def test_claiming_is_bounded(self):
        q.enqueue([{"symbol": f"C{i}", "reporting_period": "Q1FY27"} for i in range(10)])
        assert len(q.claim(limit=3)) == 3

    def test_the_oldest_is_taken_first(self):
        q.enqueue([{"symbol": "OLD", "reporting_period": "Q1FY27"}])
        q.enqueue([{"symbol": "NEW", "reporting_period": "Q1FY27"}])
        rows = _rows()
        # Force a distinguishable order.
        gateway.write(q.TAB, [{"symbol": "OLD", "reporting_period": "Q1FY27",
                               "queued_at": "2020-01-01T00:00:00+00:00"}],
                      source="test", actor="t", reason="age it")
        assert q.claim(limit=1)[0]["symbol"] == "OLD"


class TestFinishing:
    def test_success_is_recorded_with_what_it_wrote(self):
        q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])
        q.claim()
        q.finish("AAA", "Q1FY27", ok=True, datasets=["income", "balance"],
                 periods_written=2, periods_preserved=6)
        row = _rows()[0]
        assert row["status"] == q.SUCCESS
        assert row["datasets_written"] == "balance,income"
        assert row["periods_preserved"] == 6

    def test_a_failure_becomes_retry_before_it_becomes_failed(self):
        """RETRY is the system still working on it; FAILED is it asking for help."""
        q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])
        first = q.finish("AAA", "Q1FY27", ok=False, error="timeout")
        assert first["status"] == q.RETRY
        second = q.finish("AAA", "Q1FY27", ok=False, error="timeout")
        assert second["status"] == q.RETRY
        third = q.finish("AAA", "Q1FY27", ok=False, error="timeout")
        assert third["status"] == q.FAILED

    def test_a_retrying_entry_is_claimable_again(self):
        q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])
        q.claim()
        q.finish("AAA", "Q1FY27", ok=False, error="timeout")
        assert [t["symbol"] for t in q.claim()] == ["AAA"]

    def test_an_exhausted_entry_is_left_alone(self):
        """Retrying an ISIN Upstox does not recognise, forever, is not
        resilience."""
        q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])
        for _ in range(3):
            q.finish("AAA", "Q1FY27", ok=False, error="http_404")
        assert q.claim() == []
        assert q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])["skipped"] == 1


class TestSurvivingRestart:
    def test_the_queue_outlives_the_process(self):
        """The whole reason it is a table and not a list in memory."""
        q.enqueue([{"symbol": f"C{i}", "reporting_period": "Q1FY27"} for i in range(500)])
        db.reset_backend()          # a deploy
        db.init()
        assert q.queue_state()["owed"] == 500

    def test_an_entry_abandoned_mid_refresh_is_recovered(self):
        """RUNNING is not claimable, so without this a deploy landing mid-refresh
        strands those companies forever."""
        q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])
        q.claim()
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds")
        gateway.write(q.TAB, [{"symbol": "AAA", "reporting_period": "Q1FY27",
                               "started_at": old}],
                      source="test", actor="t", reason="age it")
        assert q.recover_abandoned()["recovered"] == 1
        assert [t["symbol"] for t in q.claim()] == ["AAA"]

    def test_an_entry_still_being_worked_is_left_alone(self):
        q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])
        q.claim()
        assert q.recover_abandoned()["recovered"] == 0


class TestReporting:
    def test_the_queue_says_what_it_is_holding(self):
        q.enqueue([{"symbol": "A", "reporting_period": "Q1FY27"},
                   {"symbol": "B", "reporting_period": "Q1FY27"}])
        q.finish("A", "Q1FY27", ok=True)
        state = q.queue_state()
        assert state["by_status"][q.SUCCESS] == 1
        assert state["owed"] == 1

    def test_blocked_companies_are_named(self):
        q.enqueue([{"symbol": "AAA", "reporting_period": "Q1FY27"}])
        for _ in range(3):
            q.finish("AAA", "Q1FY27", ok=False, error="unknown isin")
        blocked = q.queue_state()["failed_sample"]
        assert blocked and blocked[0]["symbol"] == "AAA"
        assert "unknown isin" in blocked[0]["error"]
