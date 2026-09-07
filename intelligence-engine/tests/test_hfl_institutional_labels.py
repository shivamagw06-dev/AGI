import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from hedge_fund_lab.production import library, strategy
from hedge_fund_lab.scanner import _scan_pairs, _scan_quality, _scan_stress, _scan_value
from hedge_fund_lab.terminal import SCANS, _SCAN_QUALIFICATION, _scan_growth, market_dashboard


def _row(ticker, value, *, industry="Mixed Industry", sector="Industrials", metric="ev_ebitda"):
    row = {
        "ticker": ticker,
        "company_name": ticker,
        "primary_sector": sector,
        "primary_industry": industry,
        "industry_dna": "capital_goods",
        "market_cap": 1e11,
        "pe": 20.0,
        "pb": 2.0,
        "ev_ebitda": 10.0,
        "roe": 20.0,
        "profit_margin": 12.0,
        "dividend_yield": 1.0,
        "consensus": {"return_1y": 10.0},
    }
    row[metric] = value
    return row


def test_impossible_ev_ebitda_is_rejected_not_surfaced():
    """1.1x EBITDA is a broken denominator, not a discount.

    It used to pass the sanity band and be surfaced with a warning label. The
    band now rejects it outright, which is what the module's own policy says:
    a value outside a plausible range is treated as missing rather than
    surfaced as an opportunity.
    """
    rows = [_row("CHEAP", 1.1)] + [_row(f"P{i}", 10 + i) for i in range(5)]
    medians = {"Mixed Industry": {"count": 6, "ev_ebitda": 10.0, "roe": 18.0}}
    assert "CHEAP" not in {hit["ticker"] for hit in _scan_value(rows, medians, 10)}


def test_suspect_but_plausible_ev_ebitda_requires_normalization():
    """A value inside the band but low enough to doubt is kept and flagged."""
    rows = [_row("SUSPECT", 3.5)] + [_row(f"P{i}", 10 + i) for i in range(5)]
    medians = {"Mixed Industry": {"count": 6, "ev_ebitda": 10.0, "roe": 18.0}}
    hit = next(h for h in _scan_value(rows, medians, 10) if h["ticker"] == "SUSPECT")
    assert hit["validation_status"] == "normalization_required"
    assert "headline" in hit["classification"].lower()


def test_pair_screen_never_claims_market_neutrality():
    rows = [_row(f"C{i}", 4 + i * 5) for i in range(6)]  # all legs inside the sanity band
    hit = _scan_pairs(rows, {"Mixed Industry": {"ev_ebitda": 10}}, 10)[0]
    assert hit["promotion_status"] == "not_market_neutral"
    assert hit["classification"] == "Valuation dispersion candidate"
    assert "cointegration and spread stationarity" in hit["required_tests"]


def test_sector_dashboard_discloses_reproducible_methodology():
    rows = [_row(f"C{i}", 8 + i) for i in range(6)]
    dash = market_dashboard(rows, {"Mixed Industry": {"count": 6, "ev_ebitda": 10.0}})
    assert dash["methodology"]["weighting"].startswith("equal-weighted")
    assert dash["interpretation"]["type"] == "agi_model_output"
    assert "book equity" in dash["metric_methodology"]["pb"]
    assert "not normalized" in dash["metric_methodology"]["ev_ebitda"]


def test_quality_debt_to_equity_requires_accounting_basis():
    row = _row("ABBOTINDIA", 20.0, metric="pe")
    row.update({"roe": 37.86, "profit_margin": 22.4, "debt_to_equity": 0.5})
    row["data_context"] = {
        "accounting_scope": "not_provided",
        "fundamentals_period": "FY26",
        "fundamentals_source": "warehouse.historical_ratios",
    }
    hit = _scan_quality([row], {}, 10)[0]
    assert hit["validation_status"] == "screen_validated"
    assert hit["comparability_status"] == "accounting_basis_verification_required"
    assert hit["debt_to_equity_basis"]["debt_definition"] == "not_provided"
    assert "verify accounting basis" in hit["why"].lower()


def test_desk_row_carries_target_and_year_ago_close():
    from hedge_fund_lab.scanner import _base

    row = _row("ZZTEST", 20.0, metric="pe")
    row["consensus"] = {
        "target_price": 840.0,
        "upside": 15.0,
        "coverage": 40,
        "buy_count": 33,
        "return_1y": -25.9,
    }
    row["data_context"] = {
        "consensus_date": "2026-08-02",
        "return_1y_base_close": 980.0,
    }
    hit = _base(row)
    assert hit["target_price"] == 840.0
    assert hit["consensus"]["target_price"] == 840.0
    assert hit["consensus_date"] == "2026-08-02"
    assert hit["return_1y_base_close"] == 980.0
    assert hit["return_1y"] == -25.9


def test_growth_binds_forward_pe_to_desk_columns():
    row = _row("GROW", 20.0, metric="pe")
    row.update({
        "pe": 40.0,
        "forward_pe": 25.0,
        "consensus": {"coverage": 10, "return_1y": 5.0},
    })
    medians = {"Mixed Industry": {"pe": 22.0, "forward_pe": 18.0}}
    hit = _scan_growth([row], medians, 10)[0]
    assert hit["forward_pe"] == 25.0
    assert hit["value"] == 25.0
    assert hit["industry_median"] == 18.0
    assert hit["implied_earnings_growth_pct"] == 60.0


def test_pair_screen_drops_extreme_spreads_and_roe_gaps():
    wide = [_row("CHEAP", 4)] + [_row(f"P{i}", 10 + i) for i in range(4)] + [_row("RICH", 50)]
    assert _scan_pairs(wide, {"Mixed Industry": {"ev_ebitda": 10}}, 10) == []

    gap = [_row(f"C{i}", 4 + i * 5) for i in range(6)]
    gap[0]["roe"] = 3.0
    gap[-1]["roe"] = 47.0
    assert _scan_pairs(gap, {"Mixed Industry": {"ev_ebitda": 10}}, 10) == []

    penny = [_row(f"C{i}", 4 + i * 5) for i in range(6)]
    penny[0]["price"] = 1.5
    assert _scan_pairs(penny, {"Mixed Industry": {"ev_ebitda": 10}}, 10) == []


def test_housing_finance_leverage_is_not_a_stress_flag():
    row = _row("BAJAJHFL", 20.0)
    row.update({
        "primary_industry": "Housing Finance",
        "debt_to_equity": 4.2,
        "profit_margin": 18.0,
        "consensus": {"return_1y": -22.0},
    })
    assert _scan_stress([row], {}, 10) == []


def test_operating_company_leverage_and_drawdown_is_stress():
    row = _row("MFG", 20.0)
    row.update({
        "primary_industry": "Cement",
        "debt_to_equity": 2.4,
        "profit_margin": 12.0,
        "consensus": {"return_1y": -25.0},
    })
    hit = _scan_stress([row], {}, 10)[0]
    assert hit["debt_to_equity"] == 2.4
    assert any("debt" in flag for flag in hit["stress_flags"])


def test_long_short_copy_discloses_residual_market_exposure():
    text = strategy("long_short_equity")["agi_intelligence"]["why_institutions_use_it"]
    assert "net beta" in text
    assert "largely independent" not in text


def test_strategy_library_is_not_production_validated():
    rows = {row["id"]: row for row in library()["strategies"]}
    assert rows["global_macro"]["status"] == "experimental"
    assert rows["long_short_equity"]["status"] == "experimental"
    assert not any(row["production_validated"] for row in rows.values())
    assert rows["long_short_equity"]["pipeline"][-1] == "live_monitoring"


def test_operational_scanners_are_not_described_as_validated_strategies():
    operational = {key for key, status in _SCAN_QUALIFICATION.items() if status[0] == "operational"}
    assert operational == {"value", "quality", "growth", "conviction", "dividend", "stress"}
    assert not any(status[0] == "production_validated" for status in _SCAN_QUALIFICATION.values())
    assert SCANS["growth"][0] == "Forward Earnings Growth"
    assert SCANS["stress"][0] == "Stress"
