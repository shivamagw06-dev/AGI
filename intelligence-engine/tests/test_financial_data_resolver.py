from financial_engine.resolver import FinancialDataResolver, _institutional_warehouse_facts


def fact(metric, value, period, *, source="regulatory_filing", unit="INR million", source_id=None, available_at="2026-05-01"):
    return {
        "canonical_metric": metric, "value": value, "reporting_period": period,
        "unit": unit, "currency": "INR", "source_type": source,
        "source_id": source_id or f"{metric}:{period}:{source}",
        "available_at": available_at, "publication_date": available_at,
        "period_end": f"{period[-4:]}-03-31", "quality": "validated",
    }


def loader_for(facts):
    return lambda company: {"ok": True, "ticker": company, "facts": facts}


def hdfc_facts():
    return [
        fact("total_equity", 5000, "FY2025"), fact("total_equity", 6000, "FY2026"),
        fact("net_income", 900, "FY2026"),
        fact("gross_loans", 10000, "FY2025"), fact("gross_loans", 11200, "FY2026"),
        fact("total_deposits", 12000, "FY2025"), fact("total_deposits", 13500, "FY2026"),
        fact("net_interest_income", 500, "FY2026"),
        fact("interest_earning_assets", 10500, "FY2025"), fact("interest_earning_assets", 12000, "FY2026"),
        fact("gross_npa", 120, "FY2026"), fact("net_npa", 35, "FY2026"),
        fact("provisions", 85, "FY2026"), fact("casa_deposits", 5400, "FY2026"),
        fact("cet1_capital", 1800, "FY2026"), fact("regulatory_capital", 2100, "FY2026"),
        fact("risk_weighted_assets", 10000, "FY2026"),
        fact("market_price", 1800, "FY2026", unit="INR per share"),
        fact("book_value_per_share", 600, "FY2026", unit="INR per share"),
    ]


def test_hdfc_warehouse_to_afe_roe_trace():
    out = FinancialDataResolver(loader_for(hdfc_facts())).calculate(
        company_id="HDFCBANK", calculation_id="ROE", period="FY2026", as_of_date="2026-08-15"
    )
    assert out["status"] == "SUCCESS"
    assert out["display_value"] == 16.36
    assert out["explanation_trace"]["formula"] == "PAT / average equity * 100"
    assert len(out["source_ids"]) == 3


def test_bank_metric_bundle_resolves_without_llm_numbers():
    resolver = FinancialDataResolver(loader_for(hdfc_facts()))
    ids = ["LOAN_GROWTH", "DEPOSIT_GROWTH", "NIM", "GNPA_RATIO", "NNPA_RATIO", "PCR", "CREDIT_COST", "ROE", "CET1_RATIO", "CRAR", "PRICE_TO_BOOK"]
    results = [resolver.calculate(company_id="HDFCBANK", calculation_id=i, period="FY2026", as_of_date="2026-08-15") for i in ids]
    assert all(row["status"] == "SUCCESS" for row in results)
    assert all(row["input_provenance"] for row in results)


def test_source_priority_and_conflict_are_explicit():
    facts = hdfc_facts() + [
        fact("net_income", 999, "FY2026", source="agi_research_extraction", source_id="lower-priority"),
    ]
    ok = FinancialDataResolver(loader_for(facts)).resolve(company_id="HDFCBANK", calculation_id="ROE", period="FY2026", as_of_date="2026-08-15")
    assert ok["status"] == "SUCCESS"
    facts.append(fact("net_income", 901, "FY2026", source="regulatory_filing", source_id="conflict"))
    conflict = FinancialDataResolver(loader_for(facts)).resolve(company_id="HDFCBANK", calculation_id="ROE", period="FY2026", as_of_date="2026-08-15")
    assert conflict["status"] == "CONFLICTING_FINANCIAL_DATA"


def test_missing_pit_units_and_staleness_fail_closed():
    missing = FinancialDataResolver(loader_for([])).resolve(company_id="AXISBANK", calculation_id="ROE", period="FY2026")
    assert missing["status"] == "DATA_UNAVAILABLE"
    future = [fact("net_income", 10, "FY2026", available_at="2026-09-01"), fact("total_equity", 100, "FY2025"), fact("total_equity", 110, "FY2026", available_at="2026-09-01")]
    pit = FinancialDataResolver(loader_for(future)).resolve(company_id="ICICIBANK", calculation_id="ROE", period="FY2026", as_of_date="2026-08-15")
    assert pit["status"] == "POINT_IN_TIME_VIOLATION"
    bad_unit = hdfc_facts()
    bad_unit[0] = fact("total_equity", 5000, "FY2025", unit="widgets")
    unit = FinancialDataResolver(loader_for(bad_unit)).resolve(company_id="HDFCBANK", calculation_id="ROE", period="FY2026")
    assert unit["status"] == "UNIT_MISMATCH"


def test_unit_normalization_crore_to_million():
    facts = [fact("net_income", 90, "FY2026", unit="INR crore"), fact("total_equity", 500, "FY2025", unit="INR crore"), fact("total_equity", 600, "FY2026", unit="INR crore")]
    out = FinancialDataResolver(loader_for(facts)).calculate(company_id="HDFCBANK", calculation_id="ROE", period="FY2026", as_of_date="2026-08-15")
    assert out["status"] == "SUCCESS"
    assert out["display_value"] == 16.36
    assert out["input_provenance"]["pat"]["reported_value"] == 90
    assert out["input_provenance"]["pat"]["normalized_value"] == 900


def test_institutional_warehouse_adapter_preserves_pit_and_provenance(monkeypatch):
    from institutional_warehouse import store

    monkeypatch.setattr(store, "fetch", lambda *args, **kwargs: {
        "rows": [{
            "row_id": "annual-1", "symbol": "HDFCBANK",
            "statement_type": "CONSOLIDATED", "fiscal_year": "FY2025",
            "fiscal_end_date": "2025-03-31", "filing_date": "2025-04-19",
            "effective_date": "2025-04-19", "source": "capital_iq_workbook",
            "pat": 673470.0, "equity": 5270100.0,
            "_meta": {"validation": "validated", "updated_at": "2025-04-20"},
        }]
    })
    facts = _institutional_warehouse_facts("HDFCBANK")
    pat = next(fact for fact in facts if fact["canonical_metric"] == "pat")
    assert pat["value"] == 673470.0
    assert pat["reporting_period"] == "FY2025"
    assert pat["available_at"] == "2025-04-19"
    assert pat["source_id"] == "annual-1"
    assert pat["statement_type"] == "CONSOLIDATED"
