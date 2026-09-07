"""Quality screen over uncovered companies, and the look-ahead it must avoid.

The panel carries fiscal year ends and no filing dates. Using FY2025 data on
2025-03-31 would rank companies on results that were not public for months, and
a quality screen is exactly where that flatters most: the figures that look
best in hindsight are the ones the market had not seen.
"""

from __future__ import annotations

import pytest

from hedge_fund_lab import neglected_quality as nq


def _ratio(symbol, sector, metric, fiscal_year, value, eligibility="ELIGIBLE"):
    return {"symbol": symbol, "sector": sector, "metric": metric,
            "fiscal_year": fiscal_year, "value": value,
            "median_eligibility": eligibility}


def _bars(symbol, month, close, day="15"):
    return {"symbol": symbol, "date": f"{month}-{day}", "close": close}


class TestFilingLag:
    def test_a_fiscal_year_is_not_usable_at_its_year_end(self):
        """FY2025 ends March 2025; audited results follow it by months."""
        assert nq.available_from("FY2025", lag_months=6) == "2025-09"

    def test_the_lag_is_configurable(self):
        assert nq.available_from("FY2025", lag_months=2) == "2025-05"

    def test_a_malformed_year_is_refused(self):
        for bad in ("", "2025", "FYXX", None, "FY99999"):
            assert nq.available_from(bad) is None

    def test_data_does_not_appear_before_it_could_be_known(self):
        rows = [_ratio(f"S{i:02d}", "IT", m, "FY2025", 10.0 + i)
                for i in range(8) for m in ("roe", "roa")]
        scores = nq.quality_scores(rows, lag_months=6)
        assert all(month >= "2025-09" for month in scores), \
            "FY2025 must not be rankable before September 2025"


class TestScoring:
    def _panel(self, n=8, sector="IT"):
        rows = []
        for i in range(n):
            for metric in ("roe", "roa", "ebitda_margin"):
                rows.append(_ratio(f"S{i:02d}", sector, metric, "FY2024", float(i)))
        return rows

    def test_higher_roe_ranks_better(self):
        scores = nq.quality_scores(self._panel())
        month = sorted(scores)[0]
        assert scores[month]["S07"] > scores[month]["S00"]

    def test_debt_equity_is_inverted(self):
        """Lower leverage is better quality; ranking it naively would reward
        the most indebted company on the board."""
        rows = []
        for i in range(8):
            rows.append(_ratio(f"S{i:02d}", "IT", "debt_equity", "FY2024", float(i)))
            rows.append(_ratio(f"S{i:02d}", "IT", "roe", "FY2024", 5.0))
        scores = nq.quality_scores(rows)
        month = sorted(scores)[0]
        assert scores[month]["S00"] > scores[month]["S07"]

    def test_ranking_happens_inside_a_sector(self):
        """A 12% ROE means different things for a bank and a software firm."""
        rows = []
        for i in range(6):
            rows.append(_ratio(f"IT{i}", "IT", "roe", "FY2024", 100.0 + i))
            rows.append(_ratio(f"IT{i}", "IT", "roa", "FY2024", 100.0 + i))
            rows.append(_ratio(f"BK{i}", "BANK", "roe", "FY2024", float(i)))
            rows.append(_ratio(f"BK{i}", "BANK", "roa", "FY2024", float(i)))
        scores = nq.quality_scores(rows)
        month = sorted(scores)[0]
        # The best bank scores like the best IT name despite far lower ROE.
        assert scores[month]["BK5"] == pytest.approx(scores[month]["IT5"])

    def test_a_missing_metric_is_not_a_zero_score(self):
        """An absent reading is not a bad reading. S07 keeps two of three
        metrics, which clears the minimum-components bar."""
        rows = self._panel()
        rows = [r for r in rows if not (r["symbol"] == "S07" and r["metric"] == "roa")]
        scores = nq.quality_scores(rows)
        month = sorted(scores)[0]
        assert scores[month]["S07"] > scores[month]["S00"]

    def test_a_thin_peer_group_is_not_ranked(self):
        rows = [_ratio(f"S{i}", "TINY", "roe", "FY2024", float(i)) for i in range(3)]
        assert nq.quality_scores(rows) == {}

    def test_vendor_excluded_rows_are_ignored(self):
        rows = self._panel()
        rows.append(_ratio("BAD", "IT", "roe", "FY2024", 9999.0, eligibility="EXCLUDED"))
        rows.append(_ratio("BAD", "IT", "roa", "FY2024", 9999.0, eligibility="EXCLUDED"))
        scores = nq.quality_scores(rows)
        assert "BAD" not in scores[sorted(scores)[0]]


class TestCoverageExclusion:
    def test_covered_companies_are_excluded(self):
        """The strategy is a bet on names nobody models; including covered
        companies would compete with every analyst in the market."""
        rows = []
        for i in range(8):
            rows.append(_ratio(f"S{i:02d}", "IT", "roe", "FY2024", float(i)))
            rows.append(_ratio(f"S{i:02d}", "IT", "roa", "FY2024", float(i)))
        scores = nq.quality_scores(rows, covered={"S07", "S06"})
        month = sorted(scores)[0]
        assert "S07" not in scores[month] and "S06" not in scores[month]
        assert "S05" in scores[month]


class TestBacktest:
    def _universe(self, n=40):
        rows, prices = [], []
        for i in range(n):
            sym = f"S{i:02d}"
            rows.append(_ratio(sym, "IT", "roe", "FY2024", float(i)))
            rows.append(_ratio(sym, "IT", "roa", "FY2024", float(i)))
            # Weekday dates: 2024-09-15 is a Sunday and would be filtered out.
            prices.append(_bars(sym, "2024-09", 100.0, "16"))
            prices.append(_bars(sym, "2024-10", 100.0 + i * 0.5, "15"))
        return rows, prices

    def test_ranks_and_measures_the_next_month(self):
        rows, prices = self._universe()
        out = nq.backtest(ratio_rows=rows, price_rows=prices, holdings=10, cost_bps=0)
        assert out["ok"] is True
        period = next(p for p in out["periods"] if p["month"] == "2024-09") \
            if "periods" in out else None
        assert out["information_coefficient"]["mean"] == pytest.approx(1.0, abs=1e-6)

    def test_fails_closed_without_a_signal(self):
        assert nq.backtest(ratio_rows=[], price_rows=[])["error"] == "no_quality_signal"

    def test_survivorship_warning_is_sharper_here(self):
        rows, prices = self._universe()
        out = nq.backtest(ratio_rows=rows, price_rows=prices, holdings=10)
        text = " ".join(out["limitations"])
        assert "SURVIVORSHIP" in text
        assert "bankrupt" in text
        assert "POINT-IN-TIME IS ASSUMED" in text
