"""Forward estimates: the conventions that would silently corrupt a screen.

`forward_pe` was null across the universe, so Forward Earnings Growth and Alpha
Opportunity both returned zero rows while the estimates sat unread in the
workbook. Wiring them up is only safe if two Capital IQ conventions are handled:
the 0 no-data sentinel, and an empty period column that forces the fiscal label
to be derived.
"""

from __future__ import annotations

from datetime import date

from financial_warehouse_completion import capiq_forward_estimates as fe


class TestFy1Selection:
    def _rows(self, *specs):
        return [
            {"symbol": s, "metric": m, "consensus_date": d, "target_period": p,
             "mean_estimate": v, "is_forward_estimate": "true"}
            for s, m, d, p, v in specs
        ]

    def test_fy1_is_chosen_over_fy2(self):
        """FY2 would understate the multiple and make a company look cheaper on
        forward earnings than anyone actually forecast."""
        rows = self._rows(
            ("AAA", "eps_estimate", "2025-12-31", "FY2026", 33.715),
            ("AAA", "eps_estimate", "2025-12-31", "FY2027", 40.818),
        )
        assert fe.latest_forward_eps(rows) == {"AAA": 33.715}

    def test_the_newest_consensus_date_wins(self):
        rows = self._rows(
            ("AAA", "eps_estimate", "2024-12-31", "FY2025", 10.0),
            ("AAA", "eps_estimate", "2025-12-31", "FY2026", 20.0),
        )
        assert fe.latest_forward_eps(rows) == {"AAA": 20.0}

    def test_a_newer_date_beats_a_nearer_period(self):
        rows = self._rows(
            ("AAA", "eps_estimate", "2024-12-31", "FY2025", 10.0),
            ("AAA", "eps_estimate", "2025-12-31", "FY2026", 20.0),
            ("AAA", "eps_estimate", "2025-12-31", "FY2027", 30.0),
        )
        assert fe.latest_forward_eps(rows) == {"AAA": 20.0}

    def test_revenue_is_not_mistaken_for_eps(self):
        rows = self._rows(("AAA", "revenue_estimate", "2025-12-31", "FY2026", 36273.9))
        assert fe.latest_forward_eps(rows) == {}

    def test_reported_actuals_are_excluded(self):
        rows = [{"symbol": "AAA", "metric": "eps_estimate", "consensus_date": "2025-12-31",
                 "target_period": "FY2026", "mean_estimate": 5.0, "is_forward_estimate": "false"}]
        assert fe.latest_forward_eps(rows) == {}

    def test_non_positive_estimates_are_dropped(self):
        """A zero or negative EPS produces a meaningless forward P/E."""
        rows = self._rows(
            ("AAA", "eps_estimate", "2025-12-31", "FY2026", 0.0),
            ("BBB", "eps_estimate", "2025-12-31", "FY2026", -3.0),
        )
        assert fe.latest_forward_eps(rows) == {}


class TestWorkbook:
    def test_parses_the_checked_in_workbook(self):
        parsed = fe.parse()
        if not parsed.get("ok"):
            return  # workbook absent in this checkout
        assert parsed["symbols"] > 800, "coverage collapsed"
        assert set(parsed["by_metric"]) == {"eps_estimate", "revenue_estimate"}

    def test_the_zero_sentinel_never_reaches_the_warehouse(self):
        """About 70% of the estimate cells are Capital IQ's no-data zero;
        reading them as forecasts implies an infinite forward P/E."""
        parsed = fe.parse()
        for row in parsed.get("rows") or []:
            assert row["mean_estimate"] != 0

    def test_periods_are_labelled_as_derived(self):
        """The export's own period column is empty for every row."""
        parsed = fe.parse()
        for row in (parsed.get("rows") or [])[:200]:
            assert row["period_source"] == "derived_indian_fy"
            assert row["is_forward_estimate"] == "true"

    def test_fy2_is_exactly_one_year_after_fy1(self):
        parsed = fe.parse()
        rows = parsed.get("rows") or []
        by_symbol: dict[str, list] = {}
        for row in rows:
            if row["metric"] == "eps_estimate":
                by_symbol.setdefault(row["symbol"], []).append(row)
        checked = 0
        for periods in by_symbol.values():
            if len(periods) < 2:
                continue
            years = sorted(int(p["target_period"][2:]) for p in periods)
            assert years[1] - years[0] == 1
            checked += 1
            if checked > 50:
                break

    def test_grain_matches_the_warehouse_key(self):
        """consensus_metric_vintages keys on
        (symbol, consensus_date, target_period, metric)."""
        rows = fe.parse().get("rows") or []
        keys = {(r["symbol"], r["consensus_date"], r["target_period"], r["metric"])
                for r in rows}
        assert len(keys) == len(rows), "duplicate rows would collapse on insert"

    def test_a_missing_workbook_fails_closed(self, tmp_path):
        out = fe.parse(path=tmp_path / "nope.xlsx")
        assert out["ok"] is False
        assert out["rows"] == []


class TestFiscalDerivation:
    def test_december_snapshot_points_at_the_march_year_end(self):
        """A 31 December 2025 pull forecasts the year ending March 2026."""
        parsed = fe.parse(as_of=date(2025, 12, 31))
        rows = [r for r in (parsed.get("rows") or []) if r["metric"] == "eps_estimate"]
        if not rows:
            return
        fy1 = sorted({r["target_period"] for r in rows})[0]
        assert fy1 == "FY2026"
        first = next(r for r in rows if r["target_period"] == "FY2026")
        assert first["target_period_end"] == "2026-03-31"
