from financial_engine import calculate, list_calculations


def test_registry_is_unique_and_versioned():
    rows = list_calculations()
    assert len(rows) >= 20
    assert len({row["calculation_id"] for row in rows}) == len(rows)
    assert all(row["version"] and row["formula"] for row in rows)


def test_roe_uses_average_equity_and_provenance():
    out = calculate(calculation_id="ROE", inputs={
        "pat": {"value": 100, "unit": "INR million", "currency": "INR", "period": "FY2026", "source_id": "pat-1", "available_at": "2026-05-01"},
        "opening_equity": {"value": 600, "unit": "INR million", "currency": "INR", "period": "FY2026", "source_id": "eq-1", "available_at": "2026-05-01"},
        "closing_equity": {"value": 650, "unit": "INR million", "currency": "INR", "period": "FY2026", "source_id": "eq-2", "available_at": "2026-05-01"},
    }, as_of="2026-06-01")
    assert out["status"] == "SUCCESS"
    assert out["display_value"] == 16.0
    assert out["source_ids"] == ["eq-1", "eq-2", "pat-1"]


def test_fail_closed_contracts():
    assert calculate(calculation_id="NOPE", inputs={})["status"] == "UNSUPPORTED_CALCULATION"
    assert calculate(calculation_id="ROE", inputs={"pat": 1})["status"] == "INSUFFICIENT_DATA"
    assert calculate(calculation_id="CASA_RATIO", inputs={"casa_deposits": 1, "total_deposits": 0})["status"] == "DIVISION_BY_ZERO"
    assert calculate(calculation_id="JUSTIFIED_PB", inputs={"roe": .16, "growth": .10, "cost_of_equity": .09})["status"] == "INVALID_TERMINAL_GROWTH"


def test_unit_period_and_pit_guards():
    mixed = calculate(calculation_id="PRICE_TO_BOOK", inputs={
        "market_price": {"value": 100, "unit": "INR", "currency": "INR", "period": "FY2026"},
        "book_value_per_share": {"value": 20, "unit": "INR million", "currency": "INR", "period": "FY2026"},
    })
    assert mixed["status"] == "UNIT_MISMATCH"
    pit = calculate(calculation_id="ROA", inputs={
        "pat": {"value": 10, "available_at": "2026-08-01"},
        "opening_assets": 100,
        "closing_assets": 110,
    }, as_of="2026-07-01")
    assert pit["status"] == "POINT_IN_TIME_VIOLATION"


def test_bank_and_telecom_examples():
    nim = calculate(calculation_id="NIM", inputs={"net_interest_income": 45, "opening_interest_earning_assets": 900, "closing_interest_earning_assets": 1100})
    assert nim["display_value"] == 4.5
    telecom = calculate(calculation_id="TELECOM_REVENUE_IMPACT", inputs={"arpu": 200, "tariff_change": .08, "subscribers": 10_000_000, "realization": .75})
    assert telecom["status"] == "SUCCESS"
    assert "SCENARIO_NOT_FACT" in telecom["warnings"]
