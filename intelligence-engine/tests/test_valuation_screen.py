from app.tools.executor import build_core_read_executor
from app.tools.registry import plan_tools, validate_tool_input
from valuation_intelligence.screen import build_screen


def _row(symbol, year, metric, value, sector="Banks"):
    return {
        "symbol": symbol, "company_name": symbol, "fiscal_year": f"FY{year}",
        "metric": metric, "value": value, "sector": "Financials", "source_sector": sector,
        "as_of": f"{year}-03-31", "source_version": "test", "median_eligibility": "ELIGIBLE",
    }


def test_screen_ranks_latest_snapshot_and_conditions_with_quality():
    rows = []
    for symbol, values, roe in (("AAA", [2.0, 1.8, 1.5], 18), ("BBB", [1.2, 1.4, 2.5], 10)):
        for year, value in zip((2023, 2024, 2025), values):
            rows.append(_row(symbol, year, "pb", value))
            rows.append(_row(symbol, year, "roe", roe))
    result = build_screen(rows, metric="p/b", sector="Banks", sort="cheapest")
    assert result["latest_fiscal_as_of"] == "2025-03-31"
    assert result["data_freshness"] == "ANNUAL_HISTORICAL_SNAPSHOT_NOT_LIVE"
    assert [row["symbol"] for row in result["rows"]] == ["AAA", "BBB"]
    assert result["rows"][0]["historical_median"] == 1.8
    assert result["rows"][0]["valuation_conditioning"]["label"] == "POTENTIALLY_ATTRACTIVE"


def test_screen_filters_discount_and_missing_history():
    rows = [_row("AAA", year, "pe", value) for year, value in zip((2023, 2024, 2025), (20, 18, 10))]
    rows += [_row("BBB", year, "pe", value) for year, value in zip((2023, 2024), (12, 11))]
    result = build_screen(rows, metric="pe", min_discount_pct=20)
    assert [row["symbol"] for row in result["rows"]] == ["AAA"]
    assert result["universe_companies"] == 1


def test_ask_agi_routes_cross_sectional_questions_to_screen():
    names = {tool["name"] for tool in plan_tools("Which banks trade below their 10-year median P/B?")["tools"]}
    assert "SCREEN_RELATIVE_VALUATION" in names
    assert "SCREEN_RELATIVE_VALUATION" in build_core_read_executor().bound_tools
    payload = validate_tool_input("SCREEN_RELATIVE_VALUATION", {"metric": "pb", "sector": "Banks", "window_years": 10})
    assert payload["sector"] == "Banks"
