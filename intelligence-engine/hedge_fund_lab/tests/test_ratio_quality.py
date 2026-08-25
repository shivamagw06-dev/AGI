"""Quality-screen ratios must be the annual warehouse print, not a scaled mess.

Algoquant ranked first on FY26 net margin 80.8% and D/E 25.5x. The company's
FY2025 disclosure is ~13.9% NPM and ~0.29x D/E; Capital IQ FY2026 is ~14.2%
and 0.25x. The defects were: string-max period picking `FY26` over `FY2026`,
D/E multiplied by 100, Upstox TTM ROE overwriting the annual figure, and a
missing 1Y return filled with 0.
"""

from __future__ import annotations

import pytest

from hedge_fund_lab import scanner
from hedge_fund_lab.ratio_audit import (
    audit_quality_metrics,
    fiscal_period_key,
    pick_latest_annual_ratio,
)


def _overlay(row):
    return dict(row), {"metrics": {}, "freshness": "FALLBACK"}


@pytest.fixture(autouse=True)
def _quiet_overlays(monkeypatch):
    monkeypatch.setattr("hedge_fund_lab.current_valuation.overlay", _overlay)
    monkeypatch.setattr(
        "valuation_ratios.ingest.apply_latest_ratios",
        lambda row, latest=None: row,
        raising=False,
    )


def _ratio(**fields):
    row = {
        "symbol": "ALGOQUANT",
        "basis": "annual",
        "period": "FY2026",
        "roe": 28.374397,
        "net_margin": 14.182463,
        "debt_equity": 0.254832,
        "gross_margin": 20.0,
        "ebitda_margin": 18.0,
    }
    row.update(fields)
    return row


class TestPeriodPicker:
    def test_fy2026_beats_the_same_year_labelled_fy26(self):
        """`'FY26' > 'FY2026'` as strings because `'6' > '0'`."""
        assert fiscal_period_key("FY2026") > fiscal_period_key("FY26")
        picked = pick_latest_annual_ratio([
            _ratio(period="FY26", net_margin=80.805632, roe=49.68, gross_margin=-25.0),
            _ratio(period="FY2026"),
        ])
        assert picked["period"] == "FY2026"
        assert picked["net_margin"] == pytest.approx(14.182463)

    def test_a_passing_year_is_preferred_over_a_later_failing_one(self):
        picked = pick_latest_annual_ratio([
            _ratio(period="FY2026", net_margin=80.8, gross_margin=-25.0, ebitda_margin=127.0),
            _ratio(period="FY2025", net_margin=13.89, roe=32.0, debt_equity=0.29),
        ])
        assert picked["period"] == "FY2025"


class TestAudit:
    def test_algoquant_fy26_formula_row_fails(self):
        audit = audit_quality_metrics(
            roe=49.68, net_margin=80.805632, debt_equity=0.254832,
            gross_margin=-25.0, ebitda_margin=127.0,
        )
        assert audit["status"] == "data_quality_fail"

    def test_scaled_debt_to_equity_fails(self):
        audit = audit_quality_metrics(roe=28.4, net_margin=13.9, debt_equity=25.5)
        assert audit["status"] == "data_quality_fail"

    def test_fy2026_capiq_row_passes(self):
        audit = audit_quality_metrics(
            roe=28.37, net_margin=14.18, debt_equity=0.255,
            computed_net_margin=14.18,
        )
        assert audit["status"] == "pass"

    def test_pat_over_revenue_disagreement_fails(self):
        audit = audit_quality_metrics(
            roe=28.4, net_margin=80.8, debt_equity=0.26,
            computed_net_margin=13.89,
        )
        assert audit["status"] == "data_quality_fail"


class TestMapping:
    def test_debt_equity_stays_a_multiple(self):
        row = scanner._map_warehouse_row(
            {"symbol": "ALGOQUANT", "cmp": 67.0, "roe": 24.84},
            ratios=_ratio(),
            factors={"momentum_12_1_pct": 0.0},
            return_1y=None,
            legacy_consensus={"return_1y": 0.0},
        )
        assert row["debt_to_equity"] == pytest.approx(0.2548, abs=0.0001)
        assert row["profit_margin"] == pytest.approx(14.182463)
        assert row["roe"] == pytest.approx(28.374397)
        assert row["consensus"]["return_1y"] is None
        assert row["data_context"]["ratio_audit"]["status"] == "pass"

    def test_a_zero_file_store_return_is_not_printed(self):
        row = scanner._map_warehouse_row(
            {"symbol": "ALGOQUANT", "cmp": 67.0},
            ratios={},
            factors={"momentum_12_1_pct": 0.0},
            return_1y=None,
            legacy_consensus={"return_1y": 0.0},
        )
        assert row["consensus"]["return_1y"] is None

    def test_a_history_return_is_kept(self):
        row = scanner._map_warehouse_row(
            {"symbol": "ALGOQUANT", "cmp": 67.0},
            ratios={},
            factors={},
            return_1y=-6.3,
            legacy_consensus={},
        )
        assert row["consensus"]["return_1y"] == pytest.approx(-6.3)


class TestQualityScan:
    def _row(self, **fields):
        base = {
            "ticker": "ALGOQUANT",
            "company_name": "Algoquant Fintech Ltd.",
            "primary_sector": "Financials",
            "primary_industry": "Capital Markets",
            "roe": 28.37,
            "profit_margin": 14.18,
            "debt_to_equity": 0.255,
            "data_context": {
                "accounting_scope": "consolidated",
                "fundamentals_period": "FY2026",
                "fundamentals_source": "warehouse.historical_ratios",
                "ratio_audit": {"status": "pass", "reasons": []},
            },
        }
        base.update(fields)
        return base

    def test_algoquant_fy2026_scores_in_the_thirties_not_sixty_four(self):
        hits = scanner._scan_quality([self._row()], {}, 15)
        assert hits[0]["roe"] == pytest.approx(28.37)
        assert hits[0]["profit_margin"] == pytest.approx(14.18)
        assert hits[0]["debt_to_equity"] == pytest.approx(0.255)
        assert hits[0]["quality_score"] == pytest.approx(28.37 + 14.18 / 2 - 0.255 * 5, abs=0.15)
        assert hits[0]["quality_score"] < 40
        assert hits[0]["validation_status"] == "screen_validated"

    def test_an_80_percent_net_margin_is_a_data_quality_fail(self):
        hits = scanner._scan_quality(
            [self._row(
                profit_margin=80.805632,
                debt_to_equity=25.48,
                data_context={
                    "accounting_scope": "not_provided",
                    "ratio_audit": audit_quality_metrics(
                        roe=24.84, net_margin=80.805632, debt_equity=25.48,
                    ),
                },
            )],
            {},
            15,
        )
        assert hits[0]["validation_status"] == "data_quality_fail"
        assert "DATA QUALITY: FAIL" in hits[0]["why"]

    def test_validated_rows_outrank_fails(self):
        hits = scanner._scan_quality(
            [
                self._row(
                    ticker="FAKE",
                    profit_margin=80.8,
                    debt_to_equity=0.3,
                    data_context={
                        "accounting_scope": "consolidated",
                        "ratio_audit": audit_quality_metrics(
                            roe=28.0, net_margin=80.8, debt_equity=0.3,
                        ),
                    },
                ),
                self._row(ticker="REAL"),
            ],
            {},
            15,
        )
        assert [h["ticker"] for h in hits] == ["REAL", "FAKE"]

    def test_leverage_gate_is_in_multiples_not_percent(self):
        high = self._row(ticker="GEARED", debt_to_equity=1.8, profit_margin=12.0, roe=16.0)
        ok = self._row(ticker="PLAIN", debt_to_equity=0.4, profit_margin=12.0, roe=16.0)
        hits = scanner._scan_quality([high, ok], {}, 15)
        tickers = [h["ticker"] for h in hits]
        assert "PLAIN" in tickers
        assert "GEARED" not in tickers
