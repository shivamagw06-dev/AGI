"""Curated views, and the specific defects each one exists to exclude.

Every filter here maps to something verified against production on 2026-08-19.
The tests name the real rows, because a filter justified only by a rule is one
refactor away from being dropped as redundant.
"""

from __future__ import annotations

from institutional_warehouse import clean_views as cv


def _patch(monkeypatch, rows):
    monkeypatch.setattr("institutional_warehouse.store.all_rows", lambda *a, **k: rows)


class TestFinancialsAnnual:
    def test_quarterly_rows_labelled_as_annual_are_rejected(self, monkeypatch):
        """RELIANCE's FY20 row reports a PAT of 63,480,000,000 - that is its
        Q4 FY20 result in absolute rupees, beside an FY2020 row in INR million
        holding the actual year. The two differ by a factor of a million."""
        _patch(monkeypatch, [
            {"symbol": "RELIANCE", "fiscal_year": "FY2020", "revenue": 5967430.0, "pat": 393540.0},
            {"symbol": "RELIANCE", "fiscal_year": "FY20", "revenue": 1392830000000.0, "pat": 63480000000.0},
        ])
        out = cv.clean_financials_annual()
        assert out["kept"] == 1
        assert out["rows"][0]["fiscal_year"] == "FY2020"
        assert out["rejected_reasons"]["quarterly_row_labelled_as_annual"] == 1

    def test_unrecognised_labels_are_rejected(self, monkeypatch):
        _patch(monkeypatch, [{"symbol": "A", "fiscal_year": "2020", "revenue": 1.0}])
        out = cv.clean_financials_annual()
        assert out["kept"] == 0
        assert out["rejected_reasons"]["unrecognised_fiscal_year_label"] == 1

    def test_rows_without_revenue_or_pat_are_rejected(self, monkeypatch):
        _patch(monkeypatch, [{"symbol": "A", "fiscal_year": "FY2020", "revenue": None, "pat": None}])
        assert cv.clean_financials_annual()["rejected_reasons"]["no_revenue_or_pat"] == 1

    def test_the_zero_sentinel_is_declared_not_silently_trusted(self, monkeypatch):
        _patch(monkeypatch, [{"symbol": "A", "fiscal_year": "FY2020", "revenue": 1.0}])
        out = cv.clean_financials_annual()
        assert out["units"] == "INR million"
        assert any("0 for no-data" in c for c in out["caveats"])
        assert any("publication dates" in c.lower() for c in out["caveats"])


class TestDailyPrices:
    def test_weekend_bars_are_rejected(self, monkeypatch):
        """MWL printed a tenth of its weekday price every Sunday for months."""
        _patch(monkeypatch, [
            {"symbol": "MWL", "date": "2026-06-19", "close": 375.85},  # Friday
            {"symbol": "MWL", "date": "2026-06-21", "close": 37.10},   # Sunday
            {"symbol": "MWL", "date": "2026-06-22", "close": 376.25},  # Monday
        ])
        out = cv.clean_daily_prices()
        assert out["kept"] == 2
        assert out["rejected_reasons"]["non_trading_day"] == 1
        assert all(r["close"] > 300 for r in out["rows"])

    def test_unusable_closes_and_dates_are_rejected(self, monkeypatch):
        _patch(monkeypatch, [
            {"symbol": "A", "date": "not-a-date", "close": 10.0},
            {"symbol": "A", "date": "2026-06-22", "close": 0},
        ])
        out = cv.clean_daily_prices()
        assert out["kept"] == 0
        assert out["rejected_reasons"]["unparseable_date"] == 1
        assert out["rejected_reasons"]["no_usable_close"] == 1

    def test_the_fake_adjusted_close_is_called_out(self, monkeypatch):
        _patch(monkeypatch, [{"symbol": "A", "date": "2026-06-22", "close": 10.0}])
        assert any("adjusted_close" in c for c in cv.clean_daily_prices()["caveats"])


class TestSectorRatios:
    def test_vendor_exclusions_are_honoured(self, monkeypatch):
        _patch(monkeypatch, [
            {"symbol": "A", "sector": "IT", "fiscal_year": "FY2020", "metric": "pe",
             "value": 20.0, "median_eligibility": "ELIGIBLE"},
            {"symbol": "A", "sector": "IT", "fiscal_year": "FY2021", "metric": "pe",
             "value": 9000.0, "median_eligibility": "EXCLUDED"},
        ])
        out = cv.clean_sector_ratios()
        assert out["kept"] == 1
        assert out["rejected_reasons"]["vendor_excluded_from_medians"] == 1


class TestReporting:
    def test_a_view_reports_both_sides_of_its_filter(self, monkeypatch):
        """A filter that quietly drops a quarter of a table is
        indistinguishable from one that is broken."""
        _patch(monkeypatch, [
            {"symbol": "A", "fiscal_year": "FY2020", "revenue": 1.0},
            {"symbol": "A", "fiscal_year": "FY20", "revenue": 1.0},
        ])
        out = cv.clean_financials_annual()
        assert out["scanned"] == 2 and out["kept"] == 1 and out["rejected"] == 1
        assert out["rejected_pct"] == 50.0

    def test_summary_covers_every_view(self, monkeypatch):
        _patch(monkeypatch, [])
        out = cv.summary()
        assert {v["view"] for v in out["views"]} == set(cv.VIEWS)
        assert all(v["ok"] for v in out["views"])

    def test_summary_reports_a_failing_view_rather_than_raising(self, monkeypatch):
        monkeypatch.setitem(cv.VIEWS, "boom", lambda limit=0: (_ for _ in ()).throw(RuntimeError("x")))
        out = cv.summary()
        assert any(v["view"] == "boom" and v["ok"] is False for v in out["views"])

    def test_an_unknown_view_lists_what_exists(self):
        out = cv.view("nope")
        assert out["ok"] is False
        assert out["error"] == "unknown_view"
        assert "sector_ratios" in out["available"]

    def test_a_warehouse_failure_degrades_to_empty(self, monkeypatch):
        def _boom(*a, **k):
            raise RuntimeError("warehouse down")

        monkeypatch.setattr("institutional_warehouse.store.all_rows", _boom)
        out = cv.clean_daily_prices()
        assert out["kept"] == 0 and out["scanned"] == 0
        assert out["rejected_pct"] == 0.0
