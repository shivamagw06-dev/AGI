import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from hedge_fund_lab.production import strategy
from hedge_fund_lab.scanner import _scan_pairs, _scan_quality, _scan_value
from hedge_fund_lab.terminal import market_dashboard


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


def test_extreme_ev_ebitda_discount_requires_normalization():
    rows = [_row("CHEAP", 1.1)] + [_row(f"P{i}", 10 + i) for i in range(5)]
    medians = {"Mixed Industry": {"count": 6, "ev_ebitda": 10.0, "roe": 18.0}}
    hit = _scan_value(rows, medians, 10)[0]
    assert hit["validation_status"] == "normalization_required"
    assert "headline" in hit["classification"].lower()


def test_pair_screen_never_claims_market_neutrality():
    rows = [_row(f"C{i}", 2 + i * 5) for i in range(6)]
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
    row.update({"roe": 37.86, "profit_margin": 22.4, "debt_to_equity": 3.6})
    row["data_context"] = {
        "accounting_scope": "not_provided",
        "fundamentals_period": "FY26",
        "fundamentals_source": "warehouse.historical_ratios",
    }
    hit = _scan_quality([row], {}, 10)[0]
    assert hit["validation_status"] == "accounting_basis_verification_required"
    assert hit["debt_to_equity_basis"]["debt_definition"] == "not_provided"
    assert "verify accounting basis" in hit["why"].lower()


def test_long_short_copy_discloses_residual_market_exposure():
    text = strategy("long_short_equity")["agi_intelligence"]["why_institutions_use_it"]
    assert "net beta" in text
    assert "largely independent" not in text
