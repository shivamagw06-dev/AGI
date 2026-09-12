from financial_engine.resolver import FinancialDataResolver


def test_pit_limited_workbook_fact_is_blocked_for_historical_calculation():
    def loader(_):
        return {"facts": [
            {"canonical_metric": "pat", "value": 100, "unit": "INR million",
             "reporting_period": "FY2025", "pit_status": "PIT_LIMITED", "source_id": "pat"},
            {"canonical_metric": "equity", "value": 900, "unit": "INR million",
             "reporting_period": "FY2024", "pit_status": "PIT_LIMITED", "source_id": "eq1"},
            {"canonical_metric": "equity", "value": 1000, "unit": "INR million",
             "reporting_period": "FY2025", "pit_status": "PIT_LIMITED", "source_id": "eq2"},
        ]}
    result = FinancialDataResolver(loader=loader).resolve(
        company_id="AAA", calculation_id="ROE", as_of_date="2025-09-30")
    assert result["status"] == "POINT_IN_TIME_UNAVAILABLE"


def test_same_fact_remains_available_for_non_pit_descriptive_analysis():
    def loader(_):
        return {"facts": [
            {"canonical_metric": "pat", "value": 100, "unit": "INR million", "reporting_period": "FY2025", "pit_status": "PIT_LIMITED"},
            {"canonical_metric": "equity", "value": 900, "unit": "INR million", "reporting_period": "FY2024", "pit_status": "PIT_LIMITED"},
            {"canonical_metric": "equity", "value": 1000, "unit": "INR million", "reporting_period": "FY2025", "pit_status": "PIT_LIMITED"},
        ]}
    result = FinancialDataResolver(loader=loader).resolve(company_id="AAA", calculation_id="ROE")
    assert result["status"] == "SUCCESS"
