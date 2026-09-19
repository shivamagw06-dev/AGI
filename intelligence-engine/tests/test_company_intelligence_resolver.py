from company_intelligence_resolver import CompanyIntelligenceResolver
from financial_engine import FinancialDataResolver


def identity(ticker, industry):
    return {
        "ticker": ticker, "company_name": ticker, "primary_sector": "Test",
        "primary_industry": industry, "industry_dna": industry,
        "business_type": "OPERATING", "country": "India", "source": "test", "resolved": True,
    }


def fact(metric, value, period="FY2026"):
    return {"canonical_metric": metric, "value": value, "reporting_period": period,
            "unit": "INR million", "currency": "INR", "source_type": "regulatory_filing",
            "source_id": f"{metric}:{period}", "available_at": "2026-05-01"}


def resolver(ticker, industry, facts):
    financial = FinancialDataResolver(loader=lambda _: {"facts": facts})
    return CompanyIntelligenceResolver(identity_loader=lambda _: identity(ticker, industry), financial_resolver=financial)


def test_bank_profile_calculates_and_exposes_missing_coverage():
    facts = [fact("net_income", 900), fact("total_equity", 5000, "FY2025"), fact("total_equity", 6000)]
    out = resolver("HDFCBANK", "banks", facts).resolve(company_id="HDFCBANK", period="FY2026", as_of_date="2026-08-15")
    items = {row["kpi"]: row for row in out["kpi_coverage"]["items"]}
    assert items["roe"]["status"] == "CALCULATED"
    assert items["nim"]["status"] == "MISSING"
    assert out["kpi_coverage"]["coverage_percent"] < 100
    assert out["fabricated"] is False


def test_telecom_profile_uses_industry_specific_raw_kpis():
    facts = [fact("arpu", 250), fact("subscribers", 400), fact("free_cash_flow", 100)]
    out = resolver("BHARTIARTL", "telecom", facts).resolve(company_id="BHARTIARTL")
    items = {row["kpi"]: row for row in out["kpi_coverage"]["items"]}
    assert items["arpu"]["status"] == "SOURCE_AVAILABLE"
    assert items["churn"]["status"] == "MISSING"


def test_old_raw_kpi_does_not_satisfy_requested_period():
    out = resolver("BHARTIARTL", "telecom", [fact("arpu", 210, "FY2025")]).resolve(
        company_id="BHARTIARTL", period="FY2026"
    )
    items = {row["kpi"]: row for row in out["kpi_coverage"]["items"]}
    assert items["arpu"]["status"] == "MISSING"


def test_multi_segment_company_combines_required_kpis_without_forcing_one_industry():
    out = resolver("RELIANCE", "conglomerates", []).resolve(
        company_id="RELIANCE",
        segments=[{"name": "Digital", "industry": "telecom", "weight": 40}, {"name": "Energy", "industry": "oil_gas", "weight": 60}],
    )
    assert len(out["segments"]) == 2
    assert {row["industry"] for row in out["segments"]} == {"telecom", "oil_gas"}
    assert out["kpi_coverage"]["required"] > 0


def test_unresolved_company_fails_closed():
    r = CompanyIntelligenceResolver(identity_loader=lambda _: {"resolved": False})
    out = r.resolve(company_id="UNKNOWN")
    assert out["status"] == "COMPANY_CLASSIFICATION_UNAVAILABLE"
