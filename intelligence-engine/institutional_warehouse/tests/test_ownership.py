"""The ownership contract, tested on the cases that would actually hurt.

Every data defect this warehouse has produced came from the same shape: two
sources writing one field with no rule about which was authoritative. A raw
price and an adjusted one shared `close` and the last writer won, which
published Dr. Lal PathLabs at -45% for a year it finished up 9.4%.

These are the failures the contract exists to make impossible.
"""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_own_"))

from institutional_warehouse import db, gateway, ownership, store  # noqa: E402


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    yield
    db.reset_backend()


class TestFieldOwnership:
    def test_upstox_cannot_write_current_ratio(self):
        """Upstox's Key Ratios endpoint returns six values and none of them is a
        liquidity ratio. A write from Upstox here is a mistake by definition."""
        out = gateway.write("historical_ratios",
                            [{"symbol": "AAA", "period": "FY2025", "basis": "annual",
                              "current_ratio": 1.8}],
                            source="upstox", actor="t", reason="test")
        assert out["ok"] is False
        assert out["error"] == "ownership_violation"
        assert out["violations"][0]["field"] == "current_ratio"
        assert out["written"] == 0

    @pytest.mark.parametrize("field", [
        "gross_margin", "operating_margin", "net_margin", "fcf_margin",
        "asset_turnover", "interest_coverage", "quick_ratio", "debt_equity"])
    def test_the_nine_ratios_upstox_does_not_supply_are_protected(self, field):
        out = gateway.write("historical_ratios",
                            [{"symbol": "AAA", "period": "FY2025", "basis": "annual",
                              field: 1.0}],
                            source="upstox", actor="t", reason="test")
        assert out["ok"] is False, f"{field} must not be writable by upstox"

    def test_the_owner_writes_the_same_field_without_complaint(self):
        out = gateway.write("historical_ratios",
                            [{"symbol": "AAA", "period": "FY2025", "basis": "annual",
                              "current_ratio": 1.8, "net_margin": 12.0}],
                            source="formula_engine", actor="t", reason="test")
        assert out["ok"] is True
        assert out["inserted"] == 1

    def test_a_violation_rejects_the_whole_write_not_just_the_field(self):
        """Half a row landing is worse than none: the rest looks complete."""
        out = gateway.write("historical_ratios",
                            [{"symbol": "AAA", "period": "FY2025", "basis": "annual",
                              "roe": 18.0, "current_ratio": 1.8}],
                            source="upstox", actor="t", reason="test")
        assert out["ok"] is False
        assert store.all_rows("historical_ratios", limit=10) == []

    def test_the_attempt_is_recorded_rather_than_swallowed(self):
        """A rejected write that leaves no trace is indistinguishable from a
        collector that was never wired up."""
        out = gateway.write("historical_ratios",
                            [{"symbol": "AAA", "period": "FY2025", "basis": "annual",
                              "quick_ratio": 1.0}],
                            source="upstox", actor="t", reason="test")
        rows = db.query(
            "SELECT action, tab_id, detail FROM wh_audit WHERE action = ?"
            " ORDER BY created_at DESC LIMIT 5", ("ownership_violation",)) or []
        assert rows, "the violation must reach the audit trail"
        assert rows[0]["tab_id"] == "historical_ratios"
        assert "quick_ratio" in str(rows[0]["detail"])
        assert out["rejected_rows"] == 1

    def test_an_unowned_field_is_left_alone(self):
        """Only contested fields are declared; declaring every column would rot
        faster than it helps."""
        assert ownership.owners_of("historical_ratios", "some_new_metric") is None


class TestHistoryIsNotTruncated:
    def test_a_shallow_source_updating_recent_periods_leaves_older_ones(self):
        """Upstox returns four annual periods where Capital IQ holds ten. The
        older six must survive the newer four arriving."""
        deep = [{"symbol": "AAA", "fiscal_year": f"FY{y}", "statement_type": "annual",
                 "revenue": 100.0 + y} for y in range(2016, 2026)]
        gateway.write("financials_annual", deep, source="capital_iq_workbook",
                      actor="t", reason="ten years")
        before = len(store.all_rows("financials_annual", limit=100))

        recent = [{"symbol": "AAA", "fiscal_year": f"FY{y}", "statement_type": "annual",
                   "revenue": 999.0} for y in range(2023, 2026)]
        gateway.write("financials_annual", recent, source="upstox", actor="t",
                      reason="four periods")

        rows = store.all_rows("financials_annual", limit=100)
        assert len(rows) == before, "a shallower source must not remove periods"
        by_year = {r["fiscal_year"]: r["revenue"] for r in rows}

        # Asserted as the invariant rather than the arithmetic: the two sources
        # declare different units, so the stored numbers are rescaled and a
        # literal here would be testing the unit converter by accident.
        untouched = {y: v for y, v in by_year.items() if y < "FY2023"}
        assert untouched == {f"FY{y}": float(100 + y) for y in range(2016, 2023)}, (
            "the six periods Upstox does not carry must be exactly as they were")
        assert by_year["FY2025"] != float(100 + 2025), "the recent period did update"

    def test_a_deep_source_cannot_be_retired_while_it_is_the_only_holder(self):
        gateway.write("daily_market_history",
                      [{"symbol": "COX&KINGS", "date": "2020-06-15", "close": 1.25}],
                      source="nse_bhavcopy", actor="t", reason="delisted")
        assert ownership.sole_holder_periods("daily_market_history", "nse_bhavcopy") >= 1


class TestCurrentSourcesCannotWriteHistory:
    def test_a_current_only_source_is_refused_an_old_period(self):
        """Upstox key ratios carry no time dimension. A row of them dated to an
        old fiscal year is not stale data, it is invented data."""
        bad = ownership.check_period_scope(
            "ratio_snapshots", [{"snapshot_date": "2019-03-31", "pe": 20.0}],
            source="upstox_key_ratios", today="2026-08-21")
        assert bad and bad[0]["rule"] == "current_source_writing_history"

    def test_today_is_fine(self):
        assert ownership.check_period_scope(
            "ratio_snapshots", [{"snapshot_date": "2026-08-21", "pe": 20.0}],
            source="upstox_key_ratios", today="2026-08-21") == []

    def test_a_deep_source_may_write_whatever_period_it_likes(self):
        assert ownership.check_period_scope(
            "financials_annual", [{"period_end": "2016-03-31"}],
            source="capital_iq_workbook", today="2026-08-21") == []


class TestPriceBasisCannotBeCrossed:
    def test_a_raw_feed_claiming_to_be_adjusted_is_refused(self):
        """The exact failure the basis column exists to prevent, arriving from a
        mislabelled writer instead of an unlabelled one."""
        out = gateway.write("daily_market_history",
                            [{"symbol": "AAA", "date": "2026-08-20", "close": 100.0,
                              "price_basis": "SPLIT_ADJUSTED"}],
                            source="nse_bhavcopy", actor="t", reason="test")
        assert out["ok"] is False
        assert out["violations"][0]["rule"] == "price_basis_mismatch"

    def test_a_feed_labelling_itself_correctly_writes(self):
        out = gateway.write("daily_market_history",
                            [{"symbol": "AAA", "date": "2026-08-20", "close": 100.0}],
                            source="nse_bhavcopy", actor="t", reason="test")
        assert out["ok"] is True


class TestFailedRefreshKeepsTheValue:
    def test_a_null_does_not_erase_a_stored_number(self):
        """A vendor having a bad morning returns nulls. Writing them turns a
        working figure on the desk into a blank with no explanation."""
        gateway.write("historical_ratios",
                      [{"symbol": "AAA", "period": "FY2025", "basis": "annual",
                        "roe": 18.5}],
                      source="formula_engine", actor="t", reason="good")
        out = gateway.write("historical_ratios",
                            [{"symbol": "AAA", "period": "FY2025", "basis": "annual",
                              "roe": None}],
                            source="formula_engine", actor="t", reason="failed refresh")
        rows = store.all_rows("historical_ratios", limit=10)
        assert rows[0]["roe"] == 18.5, "the last valid value must survive"
        assert out.get("nulls_refused", 0) >= 1, "and the refusal must be reported"

    def test_a_null_on_a_brand_new_row_is_allowed(self):
        """Nothing is being erased; the field is simply not known yet."""
        out = gateway.write("historical_ratios",
                            [{"symbol": "BBB", "period": "FY2025", "basis": "annual",
                              "roe": 12.0, "roce": None}],
                            source="formula_engine", actor="t", reason="partial")
        assert out["ok"] is True
        assert out["inserted"] == 1

    def test_a_real_value_still_replaces_an_older_one(self):
        gateway.write("historical_ratios",
                      [{"symbol": "AAA", "period": "FY2025", "basis": "annual", "roe": 18.5}],
                      source="formula_engine", actor="t", reason="first")
        gateway.write("historical_ratios",
                      [{"symbol": "AAA", "period": "FY2025", "basis": "annual", "roe": 19.9}],
                      source="formula_engine", actor="t", reason="revision")
        assert store.all_rows("historical_ratios", limit=10)[0]["roe"] == 19.9
