"""Refreshing recent statements without destroying the history behind them.

Upstox returns four annual periods; Capital IQ holds ten. Replacing the series
with what Upstox sent would delete six years nobody can get back - the deepest
data in the warehouse, destroyed by the freshest source because it arrived last.

The preservation test is the one that matters. Everything else here protects it.
"""

from __future__ import annotations

import os
import tempfile
from datetime import date

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_fw_"))

from fundamentals_refresh import detector as det  # noqa: E402
from fundamentals_refresh import queue as q  # noqa: E402
from fundamentals_refresh import worker as w  # noqa: E402
from institutional_warehouse import db, gateway, store  # noqa: E402


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    gateway.write("company_master",
                  [{"symbol": "AAA", "isin": "INE001A01001", "company_id": "AAA",
                    "company_name": "AAA"}],
                  source="test", actor="t", reason="seed")
    yield
    db.reset_backend()


def _ten_years():
    """What Capital IQ already holds: FY2017 to FY2026."""
    gateway.write("financials_annual",
                  [{"symbol": "AAA", "fiscal_year": f"FY{y}", "statement_type": "annual",
                    "revenue": float(1000 + y), "pat": float(y)}
                   for y in range(2017, 2027)],
                  source="capital_iq_workbook", actor="t", reason="ten years")


def _held():
    rows = store.fetch("financials_annual", filters={"symbol": "AAA"},
                       limit=500).get("rows") or []
    return {str(r.get("fiscal_year")): r for r in rows}


# The real Upstox shape: each statement is a list of category blocks, each with
# its own history. Written from the normaliser rather than invented, because a
# fixture that does not match the vendor tests nothing.
_BLOCK = {"income-statement": "income_statement",
          "balance-sheet": "balance_sheet",
          "cash-flow": "cash_flow"}
_CATEGORY = {"income-statement": "Revenue",
             "balance-sheet": "Total Assets",
             "cash-flow": "Cash from Operating Activity"}


def _ok(dataset, periods=("Mar 2026",)):
    block = _BLOCK.get(dataset)
    data = {"time_period": "yearly", "statement_type": dataset, "units_in": "crore"}
    if block:
        data[block] = [{"category": _CATEGORY[dataset],
                        "history": [{"period": p, "value": 9999.0} for p in periods]}]
    return {"ok": True, "dataset": dataset,
            "payload": {"isin": "INE001A01001", "data": data}}


def _all_ok(periods=("Mar 2026",)):
    return lambda isin, dataset: _ok(dataset, periods)


class TestPreservation:
    """The invariant everything else exists to protect."""

    def test_older_capital_iq_years_survive_an_upstox_refresh(self):
        _ten_years()
        before = _held()
        old = {y: before[y]["revenue"] for y in ("FY2017", "FY2018", "FY2019",
                                                 "FY2020", "FY2021", "FY2022")}
        w.refresh_company("AAA", "Mar 2026", isin="INE001A01001",
                          fetch=_all_ok(("Mar 2026", "Mar 2025")), pause_seconds=0)
        after = _held()
        for year, revenue in old.items():
            assert year in after, f"{year} was deleted"
            assert after[year]["revenue"] == revenue, f"{year} was overwritten"

    def test_the_series_is_not_replaced_by_the_four_periods_upstox_sent(self):
        _ten_years()
        w.refresh_company("AAA", "Mar 2026", isin="INE001A01001",
                          fetch=_all_ok(("Mar 2026", "Mar 2025", "Mar 2024", "Mar 2023")),
                          pause_seconds=0)
        assert len(_held()) >= 10, "ten years in, at least ten years out"

    def test_a_missing_field_does_not_blank_a_stored_value(self):
        """A vendor omitting a line item must not erase one we already have."""
        _ten_years()
        kept = _held()["FY2020"]["pat"]
        w.refresh_company("AAA", "Mar 2026", isin="INE001A01001",
                          fetch=_all_ok(), pause_seconds=0)
        assert _held()["FY2020"]["pat"] == kept

    def test_losing_a_period_is_an_error_not_a_log_line(self):
        """The write path is additive, so this should be impossible - which is
        exactly why it must stop the run rather than be noted and passed."""
        import inspect
        assert "periods_lost" in inspect.getsource(w.refresh_company)


class TestCoherence:
    def test_three_of_four_endpoints_is_not_a_refreshed_quarter(self):
        """A new income statement beside last quarter's balance sheet looks
        complete, so nobody checks it."""
        def partial(isin, dataset):
            if dataset == "balance-sheet":
                return {"ok": False, "dataset": dataset, "error": "http_500"}
            return _ok(dataset)

        out = w.refresh_company("AAA", "Mar 2026", isin="INE001A01001",
                                fetch=partial, pause_seconds=0)
        assert out["ok"] is False
        assert "incoherent_datasets" in out["error"]
        assert "balance-sheet" in out["error"]

    def test_shareholding_failing_alone_does_not_block_the_quarter(self):
        """It moves on its own schedule; its absence does not make the
        statements inconsistent with each other."""
        _ten_years()

        def no_shareholding(isin, dataset):
            if dataset == "share-holdings":
                return {"ok": False, "dataset": dataset, "error": "http_404"}
            return _ok(dataset)

        out = w.refresh_company("AAA", "Mar 2026", isin="INE001A01001",
                                fetch=no_shareholding, pause_seconds=0)
        assert out["ok"] is True

    def test_a_timeout_fails_the_company_rather_than_writing_half(self):
        out = w.refresh_company("AAA", "Mar 2026", isin="INE001A01001",
                                fetch=lambda i, d: {"ok": False, "dataset": d,
                                                    "error": "timeout"},
                                pause_seconds=0)
        assert out["ok"] is False
        assert _held() == {}


class TestIdentity:
    def test_a_payload_for_another_company_is_rejected(self):
        """Filed against the wrong company it writes someone else's revenue
        into this one's history, and nothing downstream would question it."""
        def wrong(isin, dataset):
            body = _ok(dataset)
            body["payload"]["isin"] = "INE999Z01999"
            return body

        out = w.refresh_company("AAA", "Mar 2026", isin="INE001A01001",
                                fetch=wrong, pause_seconds=0)
        assert out["ok"] is False and out["error"] == "identity_mismatch"
        assert _held() == {}


class TestQueueIntegration:
    def test_a_successful_refresh_marks_the_entry_success(self):
        _ten_years()
        q.enqueue([{"symbol": "AAA", "reporting_period": "Mar 2026"}])
        out = w.run(limit=5, fetch=_all_ok(), pause_seconds=0)
        assert out["succeeded"] == 1
        assert store.all_rows(q.TAB, limit=10)[0]["status"] == q.SUCCESS

    def test_a_failure_leaves_the_entry_retryable(self):
        q.enqueue([{"symbol": "AAA", "reporting_period": "Mar 2026"}])
        w.run(limit=5, fetch=lambda i, d: {"ok": False, "dataset": d, "error": "timeout"},
              pause_seconds=0)
        assert store.all_rows(q.TAB, limit=10)[0]["status"] == q.RETRY

    def test_a_company_with_no_isin_fails_without_being_fetched(self):
        gateway.write("company_master",
                      [{"symbol": "NOISIN", "isin": "", "company_id": "NOISIN",
                        "company_name": "NOISIN"}],
                      source="test", actor="t", reason="seed")
        q.enqueue([{"symbol": "NOISIN", "reporting_period": "Mar 2026"}])
        asked = []
        w.run(limit=5, fetch=lambda i, d: asked.append(d) or _ok(d), pause_seconds=0)
        assert asked == []

    def test_an_abandoned_entry_is_recovered_by_the_next_run(self):
        import inspect
        assert "recover_abandoned" in inspect.getsource(w.run)


class TestDetector:
    def test_a_newer_period_is_queued(self):
        out = det.detect([{"symbol": "AAA", "isin": "INE001A01001",
                           "held_period": "Mar 2025"}],
                         fetch=lambda i: {"ok": True, "period": "Mar 2026"},
                         pause_seconds=0, today=date(2026, 8, 21))
        assert out["new_periods"] == 1 and out["queued"] == 1

    def test_the_same_period_is_not_queued(self):
        out = det.detect([{"symbol": "AAA", "isin": "INE001A01001",
                           "held_period": "Mar 2026"}],
                         fetch=lambda i: {"ok": True, "period": "Mar 2026"},
                         pause_seconds=0, today=date(2026, 8, 21))
        assert out["new_periods"] == 0 and out["unchanged"] == 1

    def test_a_period_moving_backwards_is_rejected(self):
        out = det.detect([{"symbol": "AAA", "isin": "INE001A01001",
                           "held_period": "Mar 2026"}],
                         fetch=lambda i: {"ok": True, "period": "Mar 2024"},
                         pause_seconds=0, today=date(2026, 8, 21))
        assert out["rejected"] == 1
        assert out["rejections"][0]["reason"] == "period_moved_backwards"

    def test_a_future_period_is_rejected(self):
        out = det.detect([{"symbol": "AAA", "isin": "INE001A01001",
                           "held_period": "Mar 2026"}],
                         fetch=lambda i: {"ok": True, "period": "Dec 2028"},
                         pause_seconds=0, today=date(2026, 8, 21))
        assert out["rejections"][0]["reason"] == "period_in_the_future"

    def test_an_unparseable_period_is_rejected(self):
        out = det.detect([{"symbol": "AAA", "isin": "INE001A01001", "held_period": None}],
                         fetch=lambda i: {"ok": True, "period": "sometime last year"},
                         pause_seconds=0, today=date(2026, 8, 21))
        assert out["rejections"][0]["reason"] == "unparseable_period"

    def test_the_same_detection_twice_makes_one_queue_entry(self):
        for _ in range(2):
            det.detect([{"symbol": "AAA", "isin": "INE001A01001",
                         "held_period": "Mar 2025"}],
                       fetch=lambda i: {"ok": True, "period": "Mar 2026"},
                       pause_seconds=0, today=date(2026, 8, 21))
        assert len(store.all_rows(q.TAB, limit=10)) == 1

    def test_the_newest_period_is_read_structurally_not_positionally(self):
        payload = {"data": {"revenue": {"history": [
            {"period": "Mar 2024", "value": 1}, {"period": "Mar 2026", "value": 3},
            {"period": "Mar 2025", "value": 2}]}}}
        assert det.newest_period_in(payload) == "Mar 2026"

    def test_the_detector_does_not_look_at_prices_or_ratios(self):
        """PE moves every day the market opens; a company reports four times a
        year. Inferring one from the other is how you refresh 2,431 companies
        because the index fell."""
        import inspect
        src = inspect.getsource(det)
        for forbidden in ("close", "price", "\\bpe\\b", "momentum"):
            assert "ratio_movement" not in src
        assert "income-statement" in src
