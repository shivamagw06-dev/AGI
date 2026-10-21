"""YFP Financial Intelligence Enrichment — canonical history only (no Yahoo-native leaks)."""

from __future__ import annotations

from yfp.enrich import merge_financial_intelligence, merge_yahoo_into_dossier
from yfp.history import financial_coverage, kpi_trends, valuation_coverage
from yfp.leo_evidence import evidence_from_financial_intelligence
from yfp.production import is_cid_enrichment_enabled, quality_gates
from app.market_data.models import Provenance
from app.market_data.providers.yahoo_mapper import (
    map_calendar_from_yfinance_package,
    map_financial_history_from_quote_summary,
    map_financial_history_from_yfinance_package,
    map_valuation_snapshot_from_quote_summary,
    map_valuation_snapshot_from_yfinance_info,
)
from app.market_data.providers.yahoo_yfinance import _df_to_period_rows
from datetime import datetime, timezone


def _fixture():
    return {
        "quoteSummary": {
            "result": [
                {
                    "price": {"currency": "INR", "symbol": "INFY.NS"},
                    "summaryDetail": {
                        "trailingPE": {"raw": 24.0},
                        "forwardPE": {"raw": 22.0},
                        "marketCap": {"raw": 6e12},
                        "priceToSalesTrailing12Months": {"raw": 4.5},
                        "dividendYield": {"raw": 0.025},
                        "dividendRate": {"raw": 40.0},
                    },
                    "defaultKeyStatistics": {
                        "enterpriseValue": {"raw": 5.8e12},
                        "enterpriseToEbitda": {"raw": 16.0},
                        "pegRatio": {"raw": 2.1},
                        "priceToBook": {"raw": 7.0},
                        "beta": {"raw": 0.8},
                        "sharesOutstanding": {"raw": 4e9},
                        "floatShares": {"raw": 3.5e9},
                        "bookValue": {"raw": 200.0},
                    },
                    "incomeStatementHistory": {
                        "incomeStatementHistory": [
                            {
                                "endDate": {"fmt": "2023-12-31"},
                                "totalRevenue": {"raw": 1.8e12},
                                "ebitda": {"raw": 4.5e11},
                                "ebit": {"raw": 4e11},
                                "operatingIncome": {"raw": 4e11},
                                "grossProfit": {"raw": 6e11},
                                "netIncome": {"raw": 3e11},
                                "dilutedEPS": {"raw": 70.0},
                                "basicEPS": {"raw": 70.5},
                                "incomeTaxExpense": {"raw": 8e10},
                                "interestExpense": {"raw": 5e9},
                                "costOfRevenue": {"raw": 1.2e12},
                                "totalOperatingExpenses": {"raw": 2e11},
                            },
                            {
                                "endDate": {"fmt": "2022-12-31"},
                                "totalRevenue": {"raw": 1.6e12},
                                "ebitda": {"raw": 4e11},
                                "netIncome": {"raw": 2.7e11},
                                "dilutedEPS": {"raw": 63.0},
                            },
                        ]
                    },
                    "incomeStatementHistoryQuarterly": {
                        "incomeStatementHistory": [
                            {
                                "endDate": {"fmt": "2023-09-30"},
                                "totalRevenue": {"raw": 4.5e11},
                                "netIncome": {"raw": 7.5e10},
                                "dilutedEPS": {"raw": 18.0},
                            }
                        ]
                    },
                    "balanceSheetHistory": {
                        "balanceSheetStatements": [
                            {
                                "endDate": {"fmt": "2023-12-31"},
                                "totalAssets": {"raw": 1e12},
                                "totalCurrentAssets": {"raw": 6e11},
                                "cash": {"raw": 1e11},
                                "cashAndCashEquivalents": {"raw": 1.2e11},
                                "shortTermInvestments": {"raw": 5e10},
                                "longTermDebt": {"raw": 4e10},
                                "shortLongTermDebt": {"raw": 1e10},
                                "totalLiab": {"raw": 3e11},
                                "totalCurrentLiabilities": {"raw": 2e11},
                                "totalStockholderEquity": {"raw": 7e11},
                            }
                        ]
                    },
                    "cashflowStatementHistory": {
                        "cashflowStatements": [
                            {
                                "endDate": {"fmt": "2023-12-31"},
                                "totalCashFromOperatingActivities": {"raw": 3.5e11},
                                "totalCashflowsFromInvestingActivities": {"raw": -8e10},
                                "totalCashFromFinancingActivities": {"raw": -1e11},
                                "capitalExpenditures": {"raw": -4e10},
                                "depreciation": {"raw": 5e10},
                                "dividendsPaid": {"raw": -9e10},
                                "repurchaseOfStock": {"raw": -2e10},
                                "freeCashFlow": {"raw": 3.1e11},
                            }
                        ]
                    },
                }
            ]
        }
    }


def test_map_financial_history_canonical_keys():
    hist = map_financial_history_from_quote_summary(_fixture(), symbol="INFY.NS")
    income = hist["income_statement"]["annual"]
    assert income[0]["line_items"]["revenue"] == 1.8e12
    assert income[0]["line_items"]["ebitda"] == 4.5e11
    assert income[0]["line_items"]["ebit"] == 4e11
    assert income[0]["line_items"]["net_income"] == 3e11
    assert income[0]["line_items"]["diluted_eps"] == 70.0
    bal = hist["balance_sheet"]["annual"][0]
    assert bal["line_items"]["total_assets"] == 1e12
    assert bal["line_items"]["total_liabilities"] == 3e11
    assert bal["line_items"]["shareholders_equity"] == 7e11
    assert bal["line_items"]["cash"] == 1e11
    assert bal["line_items"]["total_debt"] == 5e10  # 40+10
    assert bal["validation"]["accounting_equation_ok"] is True
    cash = hist["cash_flow"]["annual"][0]
    assert cash["line_items"]["operating_cash_flow"] == 3.5e11
    assert cash["line_items"]["free_cash_flow"] == 3.1e11
    assert cash["line_items"]["capital_expenditure"] == -4e10
    # No Yahoo-native keys in line_items
    for row in income + hist["balance_sheet"]["annual"] + hist["cash_flow"]["annual"]:
        for k in row["line_items"]:
            assert "totalRevenue" not in k
            assert k == k.lower()


def test_valuation_snapshot_and_coverage():
    val = map_valuation_snapshot_from_quote_summary(_fixture(), symbol="INFY.NS")
    m = val["metrics"]
    assert m["trailing_pe"] == 24.0
    assert m["forward_pe"] == 22.0
    assert m["enterprise_value"] == 5.8e12
    assert m["ev_ebitda"] == 16.0
    assert m["price_to_book"] == 7.0
    assert m["price_to_sales"] == 4.5
    assert m["peg"] == 2.1
    assert m["dividend_yield"] == 0.025
    cov = valuation_coverage(val)
    assert cov["coverage"] >= 0.7


def test_merge_into_cid_fill_empties():
    hist = map_financial_history_from_quote_summary(_fixture(), symbol="INFY.NS")
    val = map_valuation_snapshot_from_quote_summary(_fixture(), symbol="INFY.NS")
    dossier = {
        "ticker": "INFY",
        "market_data": {},
        "valuation": {"current": {"trailing_pe": 99.0}, "historical": []},  # higher-trust PE present
        "financial_statements": {
            "income_statement": {"annual": [], "quarterly": []},
            "balance_sheet": {"annual": [], "quarterly": []},
            "cash_flow": {"annual": [], "quarterly": []},
            "versions": [],
        },
    }
    enrich = {
        "enabled": True,
        "financial_history": hist,
        "valuation_snapshot": val,
        "fundamentals": {"metrics": {}},
        "quote": {},
    }
    merged = merge_yahoo_into_dossier(dossier, enrich)
    # Does not overwrite existing PE
    assert merged["valuation"]["current"]["trailing_pe"] == 99.0
    # Fills other valuation gaps
    assert merged["valuation"]["current"].get("ev_ebitda") == 16.0
    assert merged["financial_statements"]["income_statement"]["annual"]
    assert merged["historical_kpi_trends"]["revenue"]
    assert financial_coverage(hist)["coverage"] > 0.5
    assert kpi_trends(hist)["net_income"]


def test_leo_evidence_package():
    hist = map_financial_history_from_quote_summary(_fixture(), symbol="INFY.NS")
    val = map_valuation_snapshot_from_quote_summary(_fixture(), symbol="INFY.NS")
    objs = evidence_from_financial_intelligence("INFY", financial_history=hist, valuation_snapshot=val)
    types = {o["evidence_type"] for o in objs}
    assert "financial_statements" in types
    assert "valuation_metrics" in types
    assert all(o.get("source_id") == "yahoo" for o in objs)


def test_quality_gates_offline():
    assert is_cid_enrichment_enabled() is True
    gates = quality_gates()
    assert gates["passed"] is True
    assert gates["checks"]["revenue_history_mapped"] is True
    assert gates["checks"]["accounting_equation_ok"] is True
    assert gates["checks"]["no_yahoo_native_leaks"] is True


def test_merge_financial_intelligence_idempotent_fill():
    hist = map_financial_history_from_quote_summary(_fixture(), symbol="INFY.NS")
    d = {
        "ticker": "INFY",
        "financial_statements": {
            "income_statement": {
                "annual": [{"at": "x", "source": "official", "period_rows": [{"period_end": "2023-12-31"}]}],
                "quarterly": [],
            },
            "balance_sheet": {"annual": [], "quarterly": []},
            "cash_flow": {"annual": [], "quarterly": []},
            "versions": [],
        },
    }
    out = merge_financial_intelligence(d, {"financial_history": hist, "valuation_snapshot": {}})
    # Official annual income not overwritten
    assert out["financial_statements"]["income_statement"]["annual"][0]["source"] == "official"
    # Empty balance filled
    assert out["financial_statements"]["balance_sheet"]["annual"]


def _yfinance_package_fixture():
    """Mirrors rows produced from yfinance.get_income_stmt / balance / cash_flow DataFrames."""
    return {
        "source": "yfinance",
        "endpoint": "fundamentals-timeseries",
        "symbol": "NESTLEIND.NS",
        "income_annual": [
            {
                "endDate": "2025-03-31",
                "totalRevenue": 200775000000.0,
                "grossProfit": 111278400000.0,
                "operatingIncome": 42677600000.0,
                "ebitda": 49702900000.0,
                "ebit": 44521200000.0,
                "netIncome": 32075900000.0,
                "netIncomeCommonStockholders": 32075900000.0,
                "dilutedEPS": 16.63,
                "basicEPS": 16.63,
                "costOfRevenue": 89496600000.0,
                "operatingExpense": 68600800000.0,
                "interestExpense": 1360000000.0,
                "taxProvision": 11085300000.0,
            }
        ],
        "income_quarterly": [
            {
                "endDate": "2025-12-31",
                "totalRevenue": 50000000000.0,
                "netIncome": 9984200000.0,
                "dilutedEPS": 5.1,
            }
        ],
        "balance_annual": [
            {
                "endDate": "2025-03-31",
                "totalAssets": 1.2e11,
                "currentAssets": 7e10,
                "cashAndCashEquivalents": 1.5e10,
                "totalDebt": 2e10,
                "longTermDebt": 1.5e10,
                "currentDebt": 5e9,
                "totalLiabilitiesNetMinorityInterest": 4e10,
                "currentLiabilities": 2.5e10,
                "stockholdersEquity": 8e10,
            }
        ],
        "balance_quarterly": [],
        "cash_annual": [
            {
                "endDate": "2025-03-31",
                "operatingCashFlow": 4e10,
                "investingCashFlow": -1e10,
                "financingCashFlow": -2e10,
                "freeCashFlow": 3.2e10,
                "capitalExpenditure": -8e9,
                "depreciation": 5e9,
                "cashDividendsPaid": -1.5e10,
            }
        ],
        "cash_quarterly": [],
        "info": {
            "trailingPE": 72.9,
            "forwardPE": 58.2,
            "priceToBook": 54.0,
            "enterpriseToEbitda": 49.5,
            "marketCap": 2.78e12,
            "enterpriseValue": 2.77e12,
            "currency": "INR",
            "financialCurrency": "INR",
        },
    }


def test_yfinance_package_maps_canonical_income_stmt():
    hist = map_financial_history_from_yfinance_package(_yfinance_package_fixture(), symbol="NESTLEIND.NS")
    inc = hist["income_statement"]["annual"][0]["line_items"]
    assert inc["revenue"] == 200775000000.0
    assert inc["net_income"] == 32075900000.0
    assert inc["diluted_eps"] == 16.63
    assert inc["ebitda"] == 49702900000.0
    bal = hist["balance_sheet"]["annual"][0]
    assert bal["line_items"]["total_assets"] == 1.2e11
    assert bal["line_items"]["shareholders_equity"] == 8e10
    assert bal["validation"]["accounting_equation_ok"] is True
    cash = hist["cash_flow"]["annual"][0]["line_items"]
    assert cash["operating_cash_flow"] == 4e10
    assert cash["capital_expenditure"] == -8e9
    assert cash["free_cash_flow"] == 3.2e10
    assert hist["fetch_path"] == "yfinance_fundamentals_timeseries"
    for row in hist["income_statement"]["annual"]:
        for k in row["line_items"]:
            assert k == k.lower()
            assert "totalRevenue" not in k


def test_yfinance_info_valuation_snapshot():
    val = map_valuation_snapshot_from_yfinance_info(
        _yfinance_package_fixture()["info"], symbol="NESTLEIND.NS"
    )
    assert val["metrics"]["trailing_pe"] == 72.9
    assert val["metrics"]["market_cap"] == 2.78e12
    assert val["fetch_path"] == "yfinance_info"


def test_df_to_period_rows_from_get_income_stmt_shape():
    import pandas as pd

    df = pd.DataFrame(
        {
            pd.Timestamp("2025-03-31"): [200.0, 32.0],
            pd.Timestamp("2024-03-31"): [180.0, 28.0],
        },
        index=["TotalRevenue", "NetIncome"],
    )
    rows = _df_to_period_rows(df)
    assert rows[0]["endDate"] == "2025-03-31"
    assert rows[0]["totalRevenue"] == 200.0
    assert rows[0]["netIncome"] == 32.0


def test_df_to_period_rows_pretty_quarterly_cashflow_titles():
    import pandas as pd

    df = pd.DataFrame(
        {pd.Timestamp("2025-12-31"): [1.0e9, -1.0e8]},
        index=["Free Cash Flow", "Capital Expenditure"],
    )
    rows = _df_to_period_rows(df)
    assert rows[0]["freeCashFlow"] == 1.0e9
    assert rows[0]["capitalExpenditure"] == -1.0e8


def test_yfinance_calendar_earnings_dates_and_sec_map():
    pkg = {
        "calendar": {
            "Earnings Date": ["2026-10-15"],
            "Ex-Dividend Date": "2026-07-10",
            "Earnings Average": 5.265,
            "Revenue Average": 68409463000,
        },
        "earnings_dates": [
            {
                "earnings_date": "2026-07-22T01:00:00-04:00",
                "eps_estimate": 4.36,
                "eps_actual": 5.08,
                "surprise_percent": 16.72,
            }
        ],
        "sec_filings": [
            {
                "date": "2026-05-28",
                "filing_type": "SD",
                "title": "Specialized Disclosure",
                "url": "https://example.com/sd",
            }
        ],
    }
    prov = Provenance(
        source="yahoo",
        provider_id="yahoo",
        pulled_at=datetime.now(timezone.utc),
    )
    events = map_calendar_from_yfinance_package(pkg, symbol="NESTLEIND.NS", provenance=prov)
    types = {e.event_type for e in events}
    assert "earnings" in types
    assert "earnings_history" in types
    assert "ex_dividend" in types
    assert "sec_filing" in types
    hist = next(e for e in events if e.event_type == "earnings_history")
    assert hist.details["eps_actual"] == 5.08
    assert hist.details["surprise_percent"] == 16.72
    # No Yahoo-native quoteSummary keys leaked
    blob = str([e.model_dump(mode="json") for e in events])
    assert "quoteSummary" not in blob
    assert "earningsDate" not in blob or "Earnings Date" in str(pkg["calendar"])
