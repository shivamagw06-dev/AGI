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
