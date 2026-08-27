"""Server-side calculations, search and the engine read contract."""

from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="wh_calc_"))

from institutional_warehouse import db, formulas, production, store, units  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_warehouse(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    _seed()
    yield
    db.reset_backend()


def _seed() -> None:
    store.upsert(
        "company_master",
        [
            {"company_id": "AAA", "symbol": "AAA", "company_name": "Alpha Industries",
             "sector": "Industrials", "industry": "Machinery", "active": True},
            {"company_id": "BBB", "symbol": "BBB", "company_name": "Beta Industries",
             "sector": "Industrials", "industry": "Machinery", "active": True},
            {"company_id": "CCC", "symbol": "CCC", "company_name": "Gamma Industries",
             "sector": "Industrials", "industry": "Machinery", "active": True},
        ],
        source="test", actor="tester",
    )
    annual = []
    for symbol, revenue, pat, equity in (("AAA", 1000.0, 100.0, 500.0),
                                         ("BBB", 2000.0, 150.0, 1000.0),
                                         ("CCC", 800.0, 40.0, 400.0)):
        for year, factor in (("FY2025", 0.9), ("FY2026", 1.0)):
            annual.append({
                "symbol": symbol,
                # Part of the natural key: store.upsert cannot key a row without it.
                "statement_type": "CONSOLIDATED",
                "statement_frequency": "ANNUAL",
                "fiscal_year": year,
                "revenue": revenue * factor,
                "gross_profit": revenue * factor * 0.4,
                "ebitda": revenue * factor * 0.2,
                "ebit": revenue * factor * 0.15,
                "pbt": revenue * factor * 0.13,
                "pat": pat * factor,
                "eps": (pat * factor) / 100.0,
                "assets": equity * 2 * factor,
                "equity": equity * factor,
                "debt": equity * 0.5,
                "cash": equity * 0.1,
                "current_assets": equity * 0.8,
                "current_liabilities": equity * 0.4,
                "inventory": equity * 0.2,
                "cfo": pat * factor * 1.2,
                "capex": pat * factor * 0.3,
                "shares_outstanding": 100.0,
            })
    store.upsert("financials_annual", annual, source="test", actor="tester")

    prices = []
    for symbol, base in (("AAA", 20.0), ("BBB", 45.0), ("CCC", 6.0)):
        for day in range(1, 29):
            prices.append({
                "symbol": symbol,
                "date": f"2026-07-{day:02d}",
                "open": base, "high": base * 1.02, "low": base * 0.98,
                "close": base * (1 + day / 200.0),
                "volume": 100000 + day,
                "shares_outstanding": 100.0,
            })
    store.upsert("daily_market_history", prices, source="test", actor="tester")

    store.upsert(
        "consensus",
        [
            {"symbol": "AAA", "consensus_date": "2026-07-31", "target_price": 30.0,
             "high_target": 36.0, "low_target": 24.0, "buy": 6, "outperform": 2, "hold": 2, "sell": 0},
            {"symbol": "BBB", "consensus_date": "2026-07-31", "target_price": 40.0,
             "high_target": 44.0, "low_target": 36.0, "buy": 1, "hold": 5, "sell": 3},
        ],
        source="test", actor="tester",
    )


# --------------------------------------------------------------------------
# Derived columns
# --------------------------------------------------------------------------


def test_statement_derivations_compute_fcf_and_book_value():
    formulas.recalc_statement_derivations(actor="tester")
    rows = {r["symbol"] + r["fiscal_year"]: r for r in store.fetch("financials_annual", limit=100)["rows"]}
    row = rows["AAAFY2026"]
    # Both inputs are aggregates, so free cash flow stays in INR million.
    assert row["free_cash_flow"] == pytest.approx(120.0 - 30.0)  # CFO 1.2x PAT, capex 0.3x PAT
    # Book value per share is money per share: equity of 500 INR million over
    # 100 shares is 5 million rupees a share, not 5.
    assert row["book_value"] == pytest.approx(5.0 * units.MILLION)
    assert row["source"] == "test"


def test_market_cap_is_price_times_shares():
    formulas.recalc_market_derivations(actor="tester")
    rows = store.fetch("daily_market_history", filters={"symbol": "AAA", "date": "2026-07-28"})["rows"]
    assert rows
    close = rows[0]["close"]
    assert rows[0]["market_cap"] == pytest.approx(close * 100.0)


def test_consensus_derivations_count_analysts_and_dispersion():
    formulas.recalc_consensus_derivations(actor="tester")
    row = store.fetch("consensus", filters={"symbol": "AAA"})["rows"][0]
    assert row["analyst_count"] == 10
    assert row["target_dispersion"] == pytest.approx(100.0 * (36 - 24) / 30.0)


def test_technical_features_use_12_1_momentum_and_trend():
    prices = [
        {
            "date": f"2025-{(index // 22) + 1:02d}-{(index % 22) + 1:02d}",
            "close": 100.0 + index * 0.25,
            "volume": 100_000 + index,
        }
        for index in range(280)
    ]
    out = formulas._technical_features(prices)
    assert out["momentum_12_1_pct"] is not None
    assert out["momentum_score"] is not None
    assert out["trend_score"] == 100.0
    assert out["technical_score"] is not None


# --------------------------------------------------------------------------
# Ratios
# --------------------------------------------------------------------------


def test_ratios_are_calculated_from_statements():
    formulas.recalc_statement_derivations(actor="tester")
    formulas.recalc_ratios(actor="tester")
    rows = {r["symbol"] + r["period"]: r for r in store.fetch("historical_ratios", limit=100)["rows"]}
    row = rows["AAAFY2026"]
    # ROE uses average equity across FY2025 (450) and FY2026 (500) = 475
    assert row["roe"] == pytest.approx(100.0 * 100.0 / 475.0, rel=1e-3)
    assert row["net_margin"] == pytest.approx(10.0)
    assert row["ebitda_margin"] == pytest.approx(20.0)
    assert row["debt_equity"] == pytest.approx(0.5)
    assert row["current_ratio"] == pytest.approx(2.0)
    assert row["quick_ratio"] == pytest.approx(1.5)  # (CA 400 - inventory 100) / CL 200
    assert row["basis"] == "annual"


def test_ratios_tab_is_not_manually_editable():
    formulas.recalc_ratios(actor="tester")
    row_id = store.fetch("historical_ratios")["rows"][0]["row_id"]
    result = production.edit("historical_ratios", [{"row_id": row_id, "column": "roe", "value": 1}],
                             actor="founder")
    assert result["ok"] is False


def test_annual_sector_ratio_medians_require_coverage_and_exclude_financial_leverage():
    masters = []
    ratios = []
    for index in range(10):
        symbol = f"IND{index}"
        masters.append({
            "company_id": symbol, "symbol": symbol, "company_name": f"Industrial {index}",
            "sector": "Industrials", "industry": "Machinery", "active": True,
        })
        ratios.append({
            "symbol": symbol, "period": "FY2026", "basis": "annual",
            "roe": 10.0 + index, "roce": 12.0 + index, "debt_equity": 0.5 + index / 100,
        })
    masters.append({
        "company_id": "BANK1", "symbol": "BANK1", "company_name": "Bank One",
        "sector": "Financials", "industry": "Banks", "industry_dna": "banks", "active": True,
    })
    ratios.append({
        "symbol": "BANK1", "period": "FY2026", "basis": "annual",
        "roe": 15.0, "debt_equity": 8.0,
    })
    store.upsert("company_master", masters, source="test", actor="tester")
    store.upsert("historical_ratios", ratios, source="test", actor="tester")

    formulas.recalc_annual_sector_ratios(actor="tester")
    rows = store.fetch("annual_sector_ratios", filters={"fiscal_year": "FY2026"}, limit=500)["rows"]
    industrial_roe = next(r for r in rows if r["sector"] == "Industrials" and r["metric"] == "roe")
    assert industrial_roe["quality_status"] == "PASSED"
    assert industrial_roe["company_count"] == 10
    assert industrial_roe["median_value"] == pytest.approx(14.5)
    financial_leverage = next(r for r in rows if r["sector"] == "Financials" and r["metric"] == "debt_equity")
    assert financial_leverage["quality_status"] == "NOT_APPLICABLE"
    assert financial_leverage["median_value"] is None


def test_ratios_prefer_consolidated_over_standalone_for_same_fiscal_year():
    store.upsert("financials_annual", [
        {"symbol": "AAA", "statement_type": "STANDALONE", "statement_frequency": "ANNUAL",
         "fiscal_year": "FY2024", "pat": 100.0, "equity": 500.0},
        {"symbol": "AAA", "statement_type": "CONSOLIDATED", "statement_frequency": "ANNUAL",
         "fiscal_year": "FY2024", "pat": 200.0, "equity": 1000.0},
    ], source="test", actor="tester")
    formulas.recalc_ratios(actor="tester", entity="AAA")
    row = store.fetch("historical_ratios", filters={"symbol": "AAA", "period": "FY2024"})["rows"][0]
    assert row["roe"] == pytest.approx(20.0)


# --------------------------------------------------------------------------
# Valuation
# --------------------------------------------------------------------------


def test_valuation_snapshot_computes_multiples_and_relative_position():
    formulas.recalculate(actor="tester")
    rows = {r["symbol"]: r for r in store.fetch("historical_valuation", limit=50)["rows"]}
    assert set(rows) == {"AAA", "BBB", "CCC"}
    alpha = rows["AAA"]
    assert alpha["cmp"] > 0
    assert alpha["market_cap"] == pytest.approx(alpha["cmp"] * 100.0)
    assert alpha["pe"] == pytest.approx(alpha["cmp"] / 1.0, rel=1e-6)
    # Market cap is in rupees while debt and cash are in INR million, so the
    # aggregates are converted before they are added.
    assert alpha["enterprise_value"] == pytest.approx(
        alpha["market_cap"] + (250.0 - 50.0) * units.MILLION
    )
    assert alpha["sector_median"] is not None
    assert 0 <= alpha["percentile"] <= 100
    assert alpha["upside"] == pytest.approx(100.0 * (30.0 - alpha["cmp"]) / alpha["cmp"], abs=0.01)
    assert alpha["relative_valuation_score"] is not None


def test_valuation_appends_a_new_snapshot_per_date():
    formulas.recalc_valuation(actor="tester", as_of="2026-07-30")
    formulas.recalc_valuation(actor="tester", as_of="2026-07-31")
    dates = {r["date"] for r in store.fetch("historical_valuation", limit=100)["rows"]}
    assert dates == {"2026-07-30", "2026-07-31"}


# --------------------------------------------------------------------------
# Factors
# --------------------------------------------------------------------------


def test_hedge_fund_factors_score_every_covered_company():
    formulas.recalculate(actor="tester")
    rows = {r["symbol"]: r for r in store.fetch("hedge_fund_factors", limit=50)["rows"]}
    assert set(rows) == {"AAA", "BBB", "CCC"}
    for row in rows.values():
        assert row["opportunity_score"] is not None
        assert 0 <= row["opportunity_score"] <= 100
        assert row["strategy_agreement"] >= 0


# --------------------------------------------------------------------------
# Data quality
# --------------------------------------------------------------------------


def test_data_quality_tab_reports_every_other_tab():
    formulas.recalculate(actor="tester")
    rows = {r["table_id"]: r for r in store.fetch("data_quality", limit=50)["rows"]}
    assert "company_master" in rows
    assert "data_quality" not in rows
    assert rows["company_master"]["rows"] == 3
    assert rows["company_master"]["validation_status"] in ("ok", "warn", "fail", "empty")


# --------------------------------------------------------------------------
# Search + engine contract
# --------------------------------------------------------------------------


def test_global_search_returns_rows_from_every_relevant_tab():
    formulas.recalculate(actor="tester")
    result = production.global_search("Alpha Industries")
    assert result["ok"] is True
    assert result["symbol"] == "AAA"
    tabs = {t["tab"] for t in result["tabs"]}
    assert {"company_master", "financials_annual", "historical_valuation", "consensus"} <= tabs


def test_read_company_contract_for_intelligence_modules():
    formulas.recalculate(actor="tester")
    record = production.read_company("aaa")
    assert record["ok"] is True
    assert record["symbol"] == "AAA"
    assert record["master"]["company_name"] == "Alpha Industries"
    assert record["valuation"]["pe"] is not None
    assert record["ratios"]["roe"] is not None
    assert record["factors"]["opportunity_score"] is not None
    assert record["consensus"]["target_price"] == 30.0
    assert record["coverage"]["historical_valuation"] >= 1


def test_read_table_applies_overrides_for_consumers():
    row_id = store.fetch("company_master", filters={"symbol": "AAA"})["rows"][0]["row_id"]
    production.edit("company_master", [{"row_id": row_id, "column": "sector", "value": "Capital Goods"}],
                    actor="founder", recalc=False)
    rows = {r["symbol"]: r for r in production.read_table("company_master")}
    assert rows["AAA"]["sector"] == "Capital Goods"


def test_overrides_feed_the_formula_engine():
    row_id = store.fetch("financials_annual", filters={"symbol": "AAA", "fiscal_year": "FY2026"})["rows"][0]["row_id"]
    production.edit("financials_annual", [{"row_id": row_id, "column": "pat", "value": 200.0}],
                    actor="founder", recalc=False)
    formulas.recalc_ratios(actor="tester")
    ratio = store.fetch("historical_ratios", filters={"symbol": "AAA", "period": "FY2026"})["rows"][0]
    assert ratio["net_margin"] == pytest.approx(20.0)
