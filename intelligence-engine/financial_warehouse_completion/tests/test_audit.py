"""Phase 7.4F Step 0 — coverage audit unit tests (no live warehouse)."""

from __future__ import annotations

from financial_warehouse_completion.audit import (
    CLASS_COMPLETE_10Y,
    CLASS_EMPTY,
    CLASS_GOOD,
    CLASS_MINIMAL,
    CLASS_PARTIAL,
    _classify,
    _fy_year,
    clear_audit_cache,
    run_audit,
)


def test_fy_year_parsing():
    assert _fy_year("FY24") == 2024
    assert _fy_year("FY2023") == 2023
    assert _fy_year("2019") == 2019
    assert _fy_year("") is None


def test_classify_buckets():
    assert _classify(0, 0) == CLASS_EMPTY
    assert _classify(10, 48) == CLASS_COMPLETE_10Y
    assert _classify(8, 40) == CLASS_COMPLETE_10Y
    assert _classify(7, 30) == CLASS_GOOD
    assert _classify(4, 12) == CLASS_PARTIAL
    assert _classify(2, 4) == CLASS_MINIMAL
    assert _classify(0, 5) == CLASS_MINIMAL


def test_run_audit_with_fixture(monkeypatch):
    clear_audit_cache()
    masters = [
        {"symbol": "AAA", "company_name": "Alpha", "sector": "IT", "isin": "INE1", "active": True},
        {"symbol": "BBB", "company_name": "Beta", "sector": "Banks", "isin": "INE2", "active": True},
        {"symbol": "CCC", "company_name": "Gamma", "sector": "Pharma", "active": True},
    ]
    annual = []
    for y in range(2015, 2026):
        annual.append({
            "symbol": "AAA",
            "fiscal_year": f"FY{y}",
            "statement_type": "CONSOLIDATED",
            "revenue": 100,
            "ebitda": 20,
            "ebit": 18,
            "pat": 10,
            "eps": 2,
            "assets": 200,
            "equity": 80,
            "debt": 40,
            "cash": 15,
            "cfo": 12,
            "capex": 5,
            "shares_outstanding": 50,
        })
    for y in range(2022, 2026):
        annual.append({
            "symbol": "BBB",
            "fiscal_year": f"FY{y}",
            "statement_type": "STANDALONE",
            "revenue": 50,
            "pat": 5,
        })
    quarterly = []
    for y in range(2016, 2026):
        for q in (1, 2, 3, 4):
            quarterly.append({
                "symbol": "AAA",
                "fiscal_period": f"FY{y}Q{q}",
                "fiscal_year": f"FY{y}",
                "revenue": 25,
            })
    shares = [
        {"symbol": "AAA", "as_of": "2024-03-31", "basic_shares": 50, "diluted_shares": 52, "shares_outstanding": 50},
    ]

    def fake_load(tab, *, limit=500000):
        return {
            "company_master": masters,
            "financials_annual": annual,
            "financials_quarterly": quarterly,
            "share_count_history": shares,
        }.get(tab, [])

    monkeypatch.setattr(
        "financial_warehouse_completion.audit._load_rows",
        fake_load,
    )

    out = run_audit(use_cache=False)
    assert out["ok"] is True
    assert out["read_only"] is True
    assert out["modifies_data"] is False
    s = out["summary"]
    assert s["universe"] == 3
    assert s["annual"]["ge10_years"] == 1
    assert s["quarterly"]["ge40_quarters"] == 1
    assert s["classification"][CLASS_COMPLETE_10Y] == 1
    assert s["classification"][CLASS_PARTIAL] == 1
    assert s["classification"][CLASS_EMPTY] == 1
    assert s["need_backfill"] == 2
    assert any(r["sector"] == "IT" and r["complete_10y"] == 1 for r in out["by_sector"])
    assert out["missing_fields"][0]["field"]  # ranked list present
    assert "≥10y annual" in out["plain_english"]
