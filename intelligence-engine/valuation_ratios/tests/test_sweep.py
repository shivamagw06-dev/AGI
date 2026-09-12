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


def _seed(*companies, sector=None):
    rows = [{"symbol": s, "isin": i, "company_id": s, "company_name": s,
             **({"sector": sector} if sector else {})}
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


class TestClientHeaders:
    def test_the_request_does_not_use_the_default_user_agent(self):
        """Upstox's Cloudflare answers the default urllib agent with error 1010 -
        a blocked client fingerprint, which reads as 403 and looks exactly like
        an expired token until the body is read."""
        import inspect
        src = inspect.getsource(sweep.fetch_ratios)
        assert "User-Agent" in src
        assert "Mozilla/5.0" in sweep.USER_AGENT

    def test_a_refusal_carries_the_reason_not_just_the_status(self):
        """403 alone does not distinguish an expired token from a blocked client
        from an unknown ISIN."""
        import inspect
        assert "detail" in inspect.getsource(sweep.fetch_ratios)


class TestCoverageIsTwoNumbers:
    """Eligible coverage says whether the run worked. Universe coverage says
    what AGI actually knows. Reporting only one of them misleads either way."""

    def test_both_figures_are_reported(self):
        _seed(("AAA", "INE001A01001"), ("BBB", "INE002A01002"),
              ("NOISIN1", ""), ("NOISIN2", ""))
        out = sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        assert out["universe"] == 4
        assert out["eligible"] == 2
        assert out["coverage_pct"] == 100.0, "every company that could be asked, answered"
        assert out["universe_coverage_pct"] == 50.0, "and half of AGI has no mapping"

    def test_a_run_is_healthy_on_eligible_coverage_not_universe_coverage(self):
        """283 unmapped companies are a mapping project, not a failed sweep."""
        _seed(("AAA", "INE001A01001"), *[(f"N{i}", "") for i in range(9)])
        out = sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        assert out["universe_coverage_pct"] == 10.0
        assert out["status"] == sweep.HEALTHY


class TestIncompleteIsVisibleOnTheRow:
    """A run report is read once. The rows are read for years."""

    def test_a_partial_snapshot_marks_every_one_of_its_rows(self):
        _seed(("AAA", "INE001A01001"))
        sweep.run(fetch=_ok(_payload(ev=None)), pause_seconds=0)
        rows = _stored()
        assert len(rows) == 5
        assert {r["snapshot_completeness"] for r in rows} == {"partial"}
        assert {r["snapshot_ratios_present"] for r in rows} == {5}

    def test_a_complete_snapshot_says_so(self):
        _seed(("AAA", "INE001A01001"))
        sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        rows = _stored()
        assert {r["snapshot_completeness"] for r in rows} == {"complete"}
        assert {r["snapshot_ratios_present"] for r in rows} == {6}

    def test_a_reader_can_tell_incomplete_from_absent_without_the_run_log(self):
        """The point of the column: the missing sixth ratio must not look like
        ordinary absence to whoever reads the row later."""
        _seed(("AAA", "INE001A01001"))
        sweep.run(fetch=_ok(_payload(ev=None)), pause_seconds=0)
        row = _stored()[0]
        assert row["snapshot_completeness"] == "partial"
        assert row["snapshot_ratios_present"] < len(sweep.EXPECTED)


class TestResumability:
    """The first full run was killed at twenty minutes by a deploy landing on
    top of it and lost everything. A restart should cost the batch in flight,
    not the run."""

    def test_a_second_call_skips_what_the_first_completed(self):
        _seed(*[(f"C{i}", f"INE{i:03d}A01001") for i in range(6)])
        first = sweep.run(fetch=_ok(_payload()), pause_seconds=0, max_companies=2)
        assert first["successful"] == 2
        second = sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        assert second["successful"] == 4, "only the four still owed"

    def test_a_run_that_covers_everything_leaves_nothing_owed(self):
        _seed(("AAA", "INE001A01001"), ("BBB", "INE002A01002"))
        sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        again = sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        assert again["requested"] == 0, "nothing left to fetch today"

    def test_tomorrow_starts_fresh(self):
        """Without a per-day namespace a company marked done today would be
        skipped forever, and the point of a daily snapshot is that it is daily."""
        assert sweep.kind_for("2026-08-21") != sweep.kind_for("2026-08-22")

    def test_resume_can_be_turned_off_for_a_deliberate_recollection(self):
        _seed(("AAA", "INE001A01001"))
        sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        forced = sweep.run(fetch=_ok(_payload()), pause_seconds=0, resume=False)
        assert forced["requested"] == 1

    def test_a_bounded_call_does_not_run_for_half_an_hour(self):
        """A request that long is one a deploy, a timeout or a proxy will
        eventually interrupt, and the work must survive all three."""
        _seed(*[(f"C{i}", f"INE{i:03d}A01001") for i in range(50)])
        out = sweep.run(fetch=_ok(_payload()), pause_seconds=0, max_companies=5)
        assert out["requested"] == 5

    def test_a_failed_company_is_retried_by_the_next_call(self):
        _seed(("AAA", "INE001A01001"))
        sweep.run(fetch=lambda i: {"ok": False, "error": "timeout"}, pause_seconds=0)
        retry = sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        assert retry["successful"] == 1
        assert len({r["snapshot_id"] for r in _stored()}) == 1, "one final snapshot"


class TestInstrumentClassification:
    """520 of the first sweep's 2,168 were ETFs and index funds.

    Upstox is right to have no P/E for them - they have no earnings. They were
    counted as failures, retried three times each, and pulled coverage down to
    something that read like a broken collector.
    """

    def test_an_etf_is_ineligible_not_failed(self):
        assert sweep.classify({"symbol": "NV20BEES", "isin": "INE1"}) == sweep.INELIGIBLE_ETF
        assert sweep.classify({"symbol": "GOLDBEES", "isin": "INE2"}) == sweep.INELIGIBLE_ETF

    def test_a_fund_the_symbol_does_not_reveal_is_caught_by_evidence(self):
        """ABSLLIQUID carries no ETF token and reads as a company until you ask.
        The heuristic cannot catch every one, so answering with no ratios has to
        be enough."""
        _seed(("ABSLLIQUID", "INE001A01001"))
        out = sweep.run(fetch=_ok({"data": []}), pause_seconds=0)
        assert out["invalid"] == 1
        assert out["successful"] == 0
        assert out["coverage_pct"] == 0.0 or out["answerable"] == 0

    def test_an_instrument_with_no_ratios_is_not_retried(self):
        _seed(("ABSLLIQUID", "INE001A01001"))
        sweep.run(fetch=_ok({"data": []}), pause_seconds=0)
        again = sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        assert again["requested"] == 0, "asking again three times helps nobody"

    def test_a_company_is_eligible(self):
        assert sweep.classify({"symbol": "RELIANCE", "isin": "INE1"}) == sweep.ELIGIBLE_EQUITY

    def test_no_isin_is_a_mapping_gap(self):
        assert sweep.classify({"symbol": "SOMECO", "isin": ""}) == sweep.MISSING_MAPPING

    def test_ineligible_instruments_are_skipped_never_fetched(self):
        _seed(("RELIANCE", "INE001A01001"), ("NV20BEES", "INE002A01002"))
        asked = []
        out = sweep.run(fetch=lambda i: asked.append(i) or {"ok": True, "payload": _payload()},
                        pause_seconds=0)
        assert out["eligible"] == 1, "an ETF is not in the denominator"
        assert out["skipped_no_isin"] == 1
        assert len(asked) == 1, "and is never asked about at all"

    def test_the_eligibility_breakdown_is_reported(self):
        _seed(("RELIANCE", "INE001A01001"), ("NV20BEES", "INE002A01002"),
              ("NOMAP", ""))
        out = sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        assert out["by_eligibility"][sweep.ELIGIBLE_EQUITY] == 1
        assert out["by_eligibility"][sweep.INELIGIBLE_ETF] == 1
        assert out["by_eligibility"][sweep.MISSING_MAPPING] == 1

    def test_an_etf_does_not_drag_coverage_down(self):
        _seed(("RELIANCE", "INE001A01001"), *[(f"X{i}ETF", f"INE{i:03d}A0") for i in range(9)])
        out = sweep.run(fetch=_ok(_payload()), pause_seconds=0)
        assert out["coverage_pct"] == 100.0
        assert out["status"] == sweep.HEALTHY


class TestStructuralAbsence:
    """A bank without ROCE is complete for a bank. A manufacturer without ROCE
    has a gap. The same absence, two different facts."""

    def test_a_bank_missing_roce_is_not_applicable_not_partial(self):
        assert sweep.snapshot_state(["roce", "ev_ebitda"], sector="Financials") == \
            sweep.NOT_APPLICABLE

    def test_a_manufacturer_missing_roce_is_a_real_gap(self):
        assert sweep.snapshot_state(["roce"], sector="Industrials") == sweep.PARTIAL_VALID

    def test_a_bank_missing_something_else_is_still_a_gap(self):
        assert sweep.snapshot_state(["pe"], sector="Financials") == sweep.PARTIAL_VALID

    def test_all_six_present_is_fresh(self):
        assert sweep.snapshot_state([], sector="Financials") == sweep.FRESH

    def test_a_bank_is_not_counted_incomplete_in_the_run(self):
        """Otherwise every lender reads as permanently degraded."""
        _seed(("HDFCBANK", "INE001A01001"), sector="Financials")
        out = sweep.run(fetch=_ok(_payload(roce=None, ev=None)), pause_seconds=0)
        assert out["incomplete"] == 0
        assert {r["snapshot_state"] for r in _stored()} == {sweep.NOT_APPLICABLE}


class TestRateFloor:
    """The pace was mine to choose and I chose 0.15s, which failed 218 of 254
    companies at once. It is no longer a choice."""

    def test_an_unsafe_pace_is_clamped(self):
        assert sweep.safe_pause(0.15) == sweep.MIN_PAUSE_SECONDS
        assert sweep.safe_pause(0.0) == sweep.MIN_PAUSE_SECONDS

    def test_a_slower_pace_is_allowed(self):
        assert sweep.safe_pause(3.0) == 3.0

    def test_the_default_respects_the_published_limit(self):
        # 2,000 requests per 30 minutes is about 1.1 a second.
        assert sweep.PAUSE_SECONDS >= 0.5
        assert sweep.MIN_PAUSE_SECONDS >= 0.5
