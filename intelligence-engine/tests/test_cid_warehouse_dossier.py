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
    assert dossier["peer_comparison"]["peer_group"] == ["TCS"]
    assert any(row["kind"] == "warehouse_evidence" for row in evidence_rows(dossier))
