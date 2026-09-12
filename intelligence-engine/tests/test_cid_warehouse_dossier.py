import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from cid import warehouse_dossier
from cid.openai_dossier import evidence_rows


def test_build_uses_warehouse_history_and_peers(monkeypatch):
    data = {
        "company_master": [{"symbol": "INFY", "company_name": "Infosys", "sector": "IT", "business_description": "Technology services"}],
        "financials_annual": [{"symbol": "INFY", "period": "FY25", "revenue": 100}],
        "historical_ratios": [{"symbol": "INFY", "period": "FY25", "roe": 30}],
        "historical_valuation": [{"symbol": "INFY", "date": "2026-08-12", "pe": 24}],
        "peer_relationships": [{"symbol": "INFY", "peer_symbol": "TCS"}],
    }
    monkeypatch.setattr(warehouse_dossier, "_rows", lambda table, ticker, limit: data.get(table, []))
    dossier = warehouse_dossier.build("INFY")
    assert dossier["identity"]["company_name"] == "Infosys"
    assert dossier["financial_statements"]["warehouse_annual"][0]["period"] == "FY25"
    assert dossier["financial_statements"]["income_statement"]["annual"][0]["period"] == "FY25"
    assert dossier["financial_statements"]["balance_sheet"]["annual"][0]["period"] == "FY25"
    assert dossier["financial_statements"]["cash_flow"]["annual"][0]["period"] == "FY25"
    assert "financial_statements" not in dossier["missing_evidence"]
    assert dossier["peer_comparison"]["peer_group"] == ["TCS"]
    assert any(row["kind"] == "warehouse_evidence" for row in evidence_rows(dossier))


def test_build_prefers_master_10y_inr_million_rows(monkeypatch):
    master = {
        "symbol": "INFY",
        "fiscal_year": "FY2025",
        "revenue": 100,
        "source": "capital_iq_workbook",
        "statement_version": "capiq_master_10y_fy2025",
        "_meta": {"reported_unit": "inr_million", "unit_scale": 1.0},
    }
    yahoo = {
        "symbol": "INFY",
        "fiscal_year": "FY25",
        "revenue": 100_000_000,
        "source": "formula_engine",
        "statement_version": "yahoo",
    }
    data = {
        "company_master": [{"symbol": "INFY", "company_name": "Infosys"}],
        "financials_annual": [yahoo, master],
    }
    monkeypatch.setattr(warehouse_dossier, "_rows", lambda table, ticker, limit: data.get(table, []))

    dossier = warehouse_dossier.build("INFY")

    assert dossier["financial_statements"]["income_statement"]["annual"] == [master]
    assert dossier["financial_statements"]["warehouse_annual_all_sources"] == [yahoo, master]
    assert dossier["financial_statements"]["canonical_source"]["dataset"] == "Master_10Y_India.xlsx"
    assert dossier["financial_statements"]["canonical_source"]["reported_unit"] == "inr_million"
