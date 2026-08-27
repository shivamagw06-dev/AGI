"""Ten-year valuation history on the desk screens.

`sector_ratio_history` holds 139,639 rows covering 2,627 companies over
FY2016-FY2025 across fifteen metrics, imported on 2026-08-07. Nothing in the
hedge fund lab read it: every screen ranked on a same-day cross-section, so it
could say a stock was cheaper than its neighbours but never whether it was
cheap against its own past. A sector that de-rated as a whole looked like value
in every name at once.

These pin the loader's contract and the comparison arithmetic.
"""

from __future__ import annotations

import pytest

from hedge_fund_lab import scanner


@pytest.fixture(autouse=True)
def _clear_cache():
    scanner.reset_history_cache()
    yield
    scanner.reset_history_cache()


def _rows(*specs):
    """(symbol, metric, fiscal_year, value, eligibility) -> warehouse rows."""
    return [
        {"symbol": s, "metric": m, "fiscal_year": y, "value": v, "median_eligibility": e}
        for s, m, y, v, e in specs
    ]


class TestLoader:
    def test_builds_a_median_and_span_per_symbol_metric(self, monkeypatch):
        rows = _rows(
            ("AAA", "pe", "FY2020", 10.0, "ELIGIBLE"),
            ("AAA", "pe", "FY2021", 20.0, "ELIGIBLE"),
            ("AAA", "pe", "FY2022", 30.0, "ELIGIBLE"),
        )
        monkeypatch.setattr("institutional_warehouse.store.all_rows", lambda *a, **k: rows)
        entry = scanner._valuation_history_by_symbol()["AAA"]["pe"]
        assert entry["median"] == 20.0
        assert entry["years"] == 3
        assert entry["first"] == "FY2020" and entry["last"] == "FY2022"
        assert entry["latest"] == 30.0

    def test_excluded_rows_are_not_counted(self, monkeypatch):
        """The workbook already excluded these from its own medians."""
        rows = _rows(
            ("AAA", "pe", "FY2020", 10.0, "ELIGIBLE"),
            ("AAA", "pe", "FY2021", 9000.0, "EXCLUDED"),
        )
        monkeypatch.setattr("institutional_warehouse.store.all_rows", lambda *a, **k: rows)
        out = scanner._valuation_history_by_symbol()
        assert out["AAA"]["pe"]["years"] == 1
        assert out["AAA"]["pe"]["median"] == 10.0

    def test_metrics_outside_the_screening_set_are_dropped(self, monkeypatch):
        rows = _rows(("AAA", "rd_sales", "FY2020", 1.0, "ELIGIBLE"))
        monkeypatch.setattr("institutional_warehouse.store.all_rows", lambda *a, **k: rows)
        assert scanner._valuation_history_by_symbol() == {}

    def test_unusable_values_are_skipped(self, monkeypatch):
        rows = _rows(
            ("AAA", "pe", "FY2020", None, "ELIGIBLE"),
            ("AAA", "pe", "FY2021", "n/a", "ELIGIBLE"),
            ("", "pe", "FY2021", 5.0, "ELIGIBLE"),
        )
        monkeypatch.setattr("institutional_warehouse.store.all_rows", lambda *a, **k: rows)
        assert scanner._valuation_history_by_symbol() == {}

    def test_a_warehouse_failure_degrades_to_empty(self, monkeypatch):
        def _boom(*a, **k):
            raise RuntimeError("warehouse down")

        monkeypatch.setattr("institutional_warehouse.store.all_rows", _boom)
        assert scanner._valuation_history_by_symbol() == {}


class TestOwnHistoryContext:
    def _load(self, monkeypatch, rows):
        monkeypatch.setattr("institutional_warehouse.store.all_rows", lambda *a, **k: rows)
        scanner.reset_history_cache()

    def test_cheaper_than_its_own_median_reads_negative(self, monkeypatch):
        self._load(monkeypatch, _rows(
            ("AAA", "pe", "FY2020", 20.0, "ELIGIBLE"),
            ("AAA", "pe", "FY2021", 20.0, "ELIGIBLE"),
        ))
        out = scanner.own_history_context("AAA", "pe", 15.0)
        assert out["available"] is True
        assert out["own_median"] == 20.0
        assert out["discount_vs_own_pct"] == -25.0

    def test_more_expensive_than_its_own_median_reads_positive(self, monkeypatch):
        self._load(monkeypatch, _rows(("AAA", "pe", "FY2020", 10.0, "ELIGIBLE")))
        assert scanner.own_history_context("AAA", "pe", 15.0)["discount_vs_own_pct"] == 50.0

    def test_missing_history_says_so_rather_than_returning_null(self, monkeypatch):
        """'No history' and 'no discount' are different findings."""
        self._load(monkeypatch, [])
        out = scanner.own_history_context("ZZZ", "pe", 15.0)
        assert out["available"] is False
        assert out["reason"] == "no_eligible_history"

    def test_missing_current_value_is_distinguished(self, monkeypatch):
        self._load(monkeypatch, _rows(("AAA", "pe", "FY2020", 10.0, "ELIGIBLE")))
        out = scanner.own_history_context("AAA", "pe", None)
        assert out["available"] is False
        assert out["reason"] == "no_current_value"

    def test_symbol_lookup_is_case_insensitive(self, monkeypatch):
        self._load(monkeypatch, _rows(("AAA", "pe", "FY2020", 10.0, "ELIGIBLE")))
        assert scanner.own_history_context("aaa", "PE", 10.0)["available"] is True


class TestCaching:
    def test_the_table_is_scanned_once_across_many_lookups(self, monkeypatch):
        """139,639 rows re-scanned per candidate is what took the engine down."""
        calls = {"n": 0}

        def _all_rows(*a, **k):
            calls["n"] += 1
            return _rows(("AAA", "pe", "FY2020", 10.0, "ELIGIBLE"))

        monkeypatch.setattr("institutional_warehouse.store.all_rows", _all_rows)
        scanner.reset_history_cache()
        for _ in range(25):
            scanner.own_history_context("AAA", "pe", 10.0)
        assert calls["n"] == 1

    def test_reset_forces_a_reload(self, monkeypatch):
        calls = {"n": 0}

        def _all_rows(*a, **k):
            calls["n"] += 1
            return []

        monkeypatch.setattr("institutional_warehouse.store.all_rows", _all_rows)
        scanner.reset_history_cache()
        scanner.own_history_context("AAA", "pe", 1.0)
        scanner.reset_history_cache()
        scanner.own_history_context("AAA", "pe", 1.0)
        assert calls["n"] == 2


class TestDerivedForwardPe:
    """historical_valuation.forward_pe is empty, so forward_pe was null across
    the universe and the Forward Earnings Growth and Alpha screens returned
    zero rows while the estimates sat unread in the workbook."""

    def test_price_over_fy1_eps(self):
        assert scanner.derived_forward_pe(1000.0, 50.0) == 20.0

    def test_a_loss_making_forecast_yields_no_multiple(self):
        """A negative EPS produces a negative multiple that sorts as though it
        were the cheapest name on the desk."""
        assert scanner.derived_forward_pe(1000.0, -5.0) is None

    def test_zero_eps_yields_no_multiple(self):
        assert scanner.derived_forward_pe(1000.0, 0.0) is None

    def test_missing_inputs_yield_no_multiple(self):
        assert scanner.derived_forward_pe(None, 50.0) is None
        assert scanner.derived_forward_pe(1000.0, None) is None
        assert scanner.derived_forward_pe(0.0, 50.0) is None

    def test_matches_a_hand_calculation(self):
        # 360ONE: 1,173 against an FY2026 consensus EPS of 33.715.
        assert scanner.derived_forward_pe(1173.0, 33.715) == round(1173.0 / 33.715, 2)


class TestOneYearReturn:
    """The desk showed SUNTECK at +23.1% on 2026-08-20 while the stock was down
    25.1% over the year. The price data was correct all along - 393.00 a year
    earlier against 294.25 - but the computation was disabled behind a flag and
    the displayed figure came from an uploaded file that had gone stale."""

    def test_computes_the_return_from_the_two_prices_sql_returns(self, monkeypatch):
        rows = [{"symbol": "SUNTECK", "last_close": 294.25, "base_close": 393.0}]
        monkeypatch.setattr("institutional_warehouse.db.query", lambda *a, **k: rows)
        monkeypatch.setattr("institutional_warehouse.db.physical_table", lambda t: "t")
        assert scanner._return_1y_by_symbol()["SUNTECK"] == pytest.approx(-25.13, abs=0.01)

    def test_a_rise_reads_positive(self, monkeypatch):
        rows = [{"symbol": "AAA", "last_close": 150.0, "base_close": 100.0}]
        monkeypatch.setattr("institutional_warehouse.db.query", lambda *a, **k: rows)
        monkeypatch.setattr("institutional_warehouse.db.physical_table", lambda t: "t")
        assert scanner._return_1y_by_symbol()["AAA"] == pytest.approx(50.0)

    def test_unusable_prices_are_skipped(self, monkeypatch):
        rows = [
            {"symbol": "A", "last_close": 100.0, "base_close": 0.0},
            {"symbol": "B", "last_close": None, "base_close": 100.0},
            {"symbol": "", "last_close": 100.0, "base_close": 50.0},
        ]
        monkeypatch.setattr("institutional_warehouse.db.query", lambda *a, **k: rows)
        monkeypatch.setattr("institutional_warehouse.db.physical_table", lambda t: "t")
        assert scanner._return_1y_by_symbol() == {}

    def test_it_is_no_longer_behind_a_flag(self, monkeypatch):
        """Disabling it is what let the stale file value reach the page."""
        monkeypatch.delenv("HFL_LOAD_PRICE_RETURNS", raising=False)
        rows = [{"symbol": "AAA", "last_close": 110.0, "base_close": 100.0}]
        monkeypatch.setattr("institutional_warehouse.db.query", lambda *a, **k: rows)
        monkeypatch.setattr("institutional_warehouse.db.physical_table", lambda t: "t")
        assert scanner._return_1y_by_symbol()["AAA"] == pytest.approx(10.0)

    def test_a_database_failure_degrades_to_empty(self, monkeypatch):
        def _boom(*a, **k):
            raise RuntimeError("db down")

        monkeypatch.setattr("institutional_warehouse.db.query", _boom)
        monkeypatch.setattr("institutional_warehouse.db.physical_table", lambda t: "t")
        assert scanner._return_1y_by_symbol() == {}


class TestConsensusSourcing:
    """Every desk row reported consensus_date null while the warehouse row was
    stamped 2026-08-02, so nothing on the page said how old the analyst view
    was - the same blind spot that let a year-stale 1Y return through."""

    def test_upside_is_recomputed_from_target_and_price(self):
        """SUNTECK showed 45.31% from a target of 435.93, which implies a price
        of 300.00 while the stock was at 294.25. The page prints
        u = P_target/P - 1, so it must be computed that way."""
        row = scanner._map_warehouse_row(
            {"symbol": "SUNTECK", "cmp": 294.25, "consensus_target": 435.9323,
             "consensus_upside": 45.31},
            ratios={}, factors={}, return_1y=None, legacy_consensus={},
        )
        assert row["consensus"]["upside"] == pytest.approx(48.15, abs=0.02)
        assert row["consensus"]["target_price"] == pytest.approx(435.9323)

    def test_it_falls_back_when_a_price_is_missing(self):
        row = scanner._map_warehouse_row(
            {"symbol": "AAA", "cmp": None, "consensus_upside": 12.0},
            ratios={}, factors={}, return_1y=None, legacy_consensus={},
        )
        assert row["consensus"]["upside"] == 12.0

    def test_a_zero_price_does_not_divide(self):
        row = scanner._map_warehouse_row(
            {"symbol": "AAA", "cmp": 0.0, "consensus_target": 100.0},
            ratios={}, factors={}, return_1y=None, legacy_consensus={},
        )
        assert row["consensus"]["upside"] is None

    def test_the_consensus_date_reaches_the_row(self):
        row = scanner._map_warehouse_row(
            {"symbol": "AAA", "cmp": 100.0, "consensus_date": "2026-08-02"},
            ratios={}, factors={}, return_1y=None, legacy_consensus={},
        )
        assert row["data_context"]["consensus_date"] == "2026-08-02"


class TestTradedClose:
    """historical_valuation.cmp does not agree with the market. Against
    daily_market_history on 2026-08-19, 1,050 of 1,162 symbols differed and
    only 112 matched - RSDFIN at 152.44 against a true close of 96.15."""

    def test_returns_the_last_traded_close(self, monkeypatch):
        rows = [{"symbol": "RSDFIN", "close": 96.15}, {"symbol": "SUNTECK", "close": 294.25}]
        monkeypatch.setattr("institutional_warehouse.db.query", lambda *a, **k: rows)
        monkeypatch.setattr("institutional_warehouse.db.physical_table", lambda t: "t")
        out = scanner._latest_close_by_symbol()
        assert out["RSDFIN"] == 96.15 and out["SUNTECK"] == 294.25

    def test_unusable_rows_are_skipped(self, monkeypatch):
        rows = [{"symbol": "A", "close": 0}, {"symbol": "", "close": 10.0},
                {"symbol": "B", "close": None}]
        monkeypatch.setattr("institutional_warehouse.db.query", lambda *a, **k: rows)
        monkeypatch.setattr("institutional_warehouse.db.physical_table", lambda t: "t")
        assert scanner._latest_close_by_symbol() == {}

    def test_a_database_failure_degrades_to_empty(self, monkeypatch):
        def _boom(*a, **k):
            raise RuntimeError("db down")

        monkeypatch.setattr("institutional_warehouse.db.query", _boom)
        monkeypatch.setattr("institutional_warehouse.db.physical_table", lambda t: "t")
        assert scanner._latest_close_by_symbol() == {}

    def test_the_traded_close_drives_upside(self):
        """With cmp corrected to 294.25, a 435.93 target is 48.15% away, not
        the 45.31% the valuation table's 300.00 implied."""
        row = scanner._map_warehouse_row(
            {"symbol": "SUNTECK", "cmp": 294.25},
            ratios={}, factors={}, return_1y=None,
            legacy_consensus={"target_price": 435.9323},
        )
        assert row["price"] == 294.25
        assert row["consensus"]["upside"] == pytest.approx(48.15, abs=0.02)
