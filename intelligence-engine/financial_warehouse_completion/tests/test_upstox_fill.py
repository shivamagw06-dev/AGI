"""Upstox EMPTY-fill queue unit tests."""

from __future__ import annotations

from financial_warehouse_completion.upstox_fill import queue_candidates
from financial_warehouse_completion.yahoo_fill import clear_queue_cache


def test_upstox_queue_requires_ine_isin(monkeypatch):
    clear_queue_cache()
    masters = [
        {"symbol": "EMPTY1", "company_name": "Empty Equity", "sector": "IT", "isin": "INE025R01021"},
        {"symbol": "FUND1", "company_name": "Some Fund", "sector": "Unknown", "isin": "INF209KC1670"},
        {"symbol": "NOISIN", "company_name": "No Isin Co", "sector": "IT"},
    ]

    def fake_load(tab, *, limit=500000):
        return {
            "company_master": masters,
            "financials_annual": [],
            "financials_quarterly": [],
            "share_count_history": [],
        }.get(tab, [])

    monkeypatch.setattr("financial_warehouse_completion.audit._load_rows", fake_load)
    monkeypatch.setattr("financial_warehouse_completion.audit.clear_audit_cache", lambda: None)
    q = queue_candidates(limit=50, include_thin=True)
    symbols = [r["symbol"] for r in q["rows"]]
    assert symbols == ["EMPTY1"]
    assert q["counts"]["empty"] == 1
    assert q["counts"]["skipped_non_equity"] >= 1
    assert q["source"] == "upstox"

    q2 = queue_candidates(limit=50, include_thin=True, exclude=["EMPTY1"])
    assert q2["rows"] == []
    assert q2["counts"]["skipped_excluded"] == 1
