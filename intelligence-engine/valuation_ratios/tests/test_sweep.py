"""The daily key-ratio sweep, tested on the ways a sweep goes wrong.

Upstox's Key Ratios endpoint has no time dimension - it returns today's six
values and nothing else. So every day not collected is a day that cannot be
recovered, and a sweep that quietly covers 3% of the universe while reporting
success is worse than one that fails loudly.
"""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_sweep_"))

from institutional_warehouse import db, gateway, store  # noqa: E402
from valuation_ratios import sweep  # noqa: E402


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "test-token")
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


def _seed(*companies):
    rows = [{"symbol": s, "isin": i, "company_id": s, "company_name": s}
            for s, i in companies]
    gateway.write("company_master", rows, source="test", actor="t", reason="seed")


def _payload(pe=20.0, pb=3.0, roa=8.0, roe=15.0, roce=18.0, ev=12.0, **over):
    values = {"pe": pe, "pb": pb, "roa": roa, "roe": roe, "roce": roce,
              "ev/ebitda": ev}
    values.update(over)
    return {"data": [{"name": k, "company_value": v} for k, v in values.items()
                     if v is not None]}


def _ok(payload):
    return lambda isin: {"ok": True, "payload": payload}


def _stored():
    return store.all_rows("valuation_ratios", limit=500)


class TestHappyPath:
    def test_a_company_yields_six_ratio_rows(self):
        _seed(("AAA", "INE001A01001"))
        out = sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        assert out["successful"] == 1
        assert {r["ratio_name"] for r in _stored()} == set(sweep.EXPECTED)

    def test_the_run_is_recorded_with_coverage_and_status(self):
        _seed(("AAA", "INE001A01001"), ("BBB", "INE002A01002"))
        out = sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        assert out["eligible"] == 2 and out["successful"] == 2
        assert out["coverage_pct"] == 100.0
        assert out["status"] == sweep.HEALTHY
        assert out["run_id"]


class TestIdempotence:
    def test_running_twice_in_a_day_does_not_duplicate(self):
        """snapshot_id is part of the key. A random one made a re-run land a
        second row for the same company on the same date."""
        _seed(("AAA", "INE001A01001"))
        sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        first = len(_stored())
        sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        assert len(_stored()) == first, "a second sweep must not double the rows"

    def test_a_retry_after_failure_leaves_one_snapshot(self):
        _seed(("AAA", "INE001A01001"))
        sweep.run(fetch=lambda i: {"ok": False, "error": "timeout"}, pause_seconds=0)
        assert _stored() == []
        sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        assert len({r["snapshot_id"] for r in _stored()}) == 1


class TestFailuresDoNotCorrupt:
    def test_a_failed_call_writes_nothing_at_all(self):
        """A null is not a reading. Writing one turns a good figure on the desk
        into a blank with no explanation."""
        _seed(("AAA", "INE001A01001"))
        out = sweep.run(fetch=lambda i: {"ok": False, "error": "http_500"},
                        pause_seconds=0)
        assert _stored() == []
        assert out["failed"] == 1 and out["successful"] == 0
        assert out["status"] == sweep.FAILED

    def test_yesterdays_snapshot_survives_todays_failure(self):
        _seed(("AAA", "INE001A01001"))
        sweep.run(fetch=_ok(_payload(pe=20.0)), pause_seconds=0)
        before = [r for r in _stored() if r["ratio_name"] == "pe"][0]["company_value"]
        sweep.run(fetch=lambda i: {"ok": False, "error": "timeout"}, pause_seconds=0)
        after = [r for r in _stored() if r["ratio_name"] == "pe"][0]["company_value"]
        assert after == before == 20.0

    def test_one_bad_company_does_not_stop_the_others(self):
        """A batch that aborts on the first bad payload loses the healthy
        companies behind it."""
        _seed(("AAA", "INE001A01001"), ("BAD", "INE0BAD01001"), ("CCC", "INE003A01003"))

        def flaky(isin):
            if isin == "INE0BAD01001":
                raise RuntimeError("upstream exploded")
            return {"ok": True, "payload": _payload()}

        def guarded(isin):
            try:
                return flaky(isin)
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        out = sweep.run(fetch=guarded, pause_seconds=0)
        assert out["successful"] == 2 and out["failed"] == 1
        assert {r["symbol"] for r in _stored()} == {"AAA", "CCC"}

    def test_an_unreadable_response_is_counted_invalid_not_empty(self):
        _seed(("AAA", "INE001A01001"))
        out = sweep.run(fetch=_ok({"data": [{"name": "nonsense", "company_value": 1}]}),
                        pause_seconds=0)
        assert out["invalid"] == 1 and out["successful"] == 0
        assert _stored() == []


class TestIncompleteResponses:
    def test_five_of_six_is_recorded_as_incomplete(self):
        """Promoted with what it has and flagged, because pretending otherwise
        makes a gap look like a value nobody questioned."""
        _seed(("AAA", "INE001A01001"))
        out = sweep.run(fetch=_ok(_payload(ev=None)), pause_seconds=0)
        assert out["incomplete"] == 1
        assert out["incomplete_sample"][0]["missing"] == ["ev_ebitda"]
        assert len(_stored()) == 5

    def test_a_complete_response_is_not_flagged(self):
        _seed(("AAA", "INE001A01001"))
        assert sweep.run(fetch=_ok(_payload()), pause_seconds=0)["incomplete"] == 0


class TestCoverageHonesty:
    def test_a_company_without_an_isin_is_skipped_with_a_reason(self):
        """283 unmapped companies are a mapping gap, not 283 broken calls, and
        must not drag the coverage figure down as if they were."""
        _seed(("AAA", "INE001A01001"), ("NOISIN", ""))
        out = sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        assert out["skipped_no_isin"] == 1
        assert out["eligible"] == 1
        assert out["coverage_pct"] == 100.0

    def test_a_partial_sweep_is_degraded_not_healthy(self):
        _seed(*[(f"C{i}", f"INE{i:03d}A01001") for i in range(10)])

        def half(isin):
            return ({"ok": True, "payload": _payload()} if isin.endswith("1001")
                    and int(isin[3:6]) < 5 else {"ok": False, "error": "http_400"})

        out = sweep.run(fetch=half, pause_seconds=0)
        assert out["coverage_pct"] == 50.0
        assert out["status"] == sweep.DEGRADED, "half a universe is not a daily snapshot"

    def test_the_healthy_bar_is_the_one_agreed(self):
        assert sweep.HEALTHY_COVERAGE_PCT == 95.0


class TestOwnershipStillApplies:
    def test_the_sweep_writes_through_the_gateway(self):
        """So the ownership contract validates every promoted row rather than
        the collector being trusted to behave."""
        import inspect
        src = inspect.getsource(sweep.run)
        assert "gateway.write" in src
        assert "store.upsert" not in src
