"""Yahoo-first fill unit tests — mocked warehouse / Yahoo loader."""

from __future__ import annotations

from financial_warehouse_completion.yahoo_fill import (
    _looks_non_equity,
    clear_queue_cache,
    fill_company,
    queue_candidates,
    run_batch,
    status,
)


def test_skips_etf_like_symbols():
    assert _looks_non_equity("ABSLBANETF") is True
    assert _looks_non_equity("NIFTYBEES") is True
    assert _looks_non_equity("RELIANCE", isin="INE002A01018") is False
    assert _looks_non_equity("ABSL10BANK", isin="INF209KC1670") is True
    assert _looks_non_equity("FOO", "Some Index ETF Fund") is True


def test_queue_candidates_priority(monkeypatch):
    clear_queue_cache()
    masters = [
        {"symbol": "EMPTY1", "company_name": "Empty Co", "sector": "IT"},
        {"symbol": "THIN1", "company_name": "Thin Co", "sector": "Banks"},
        {"symbol": "ETF1", "company_name": "Nifty ETF", "sector": "Unknown", "isin": "INF209KC9999"},
        {"symbol": "OK1", "company_name": "Ok Co", "sector": "IT"},
    ]
    annual = [
        {"symbol": "THIN1", "fiscal_year": "FY24", "revenue": 1, "pat": 1},
        {"symbol": "THIN1", "fiscal_year": "FY25", "revenue": 1, "pat": 1},
        {"symbol": "OK1", "fiscal_year": "FY22", "revenue": 1},
        {"symbol": "OK1", "fiscal_year": "FY23", "revenue": 1},
        {"symbol": "OK1", "fiscal_year": "FY24", "revenue": 1},
        {"symbol": "OK1", "fiscal_year": "FY25", "revenue": 1},
    ]
    quarterly = [
        {"symbol": "OK1", "fiscal_period": "FY25Q1", "revenue": 1},
        {"symbol": "OK1", "fiscal_period": "FY25Q2", "revenue": 1},
        {"symbol": "OK1", "fiscal_period": "FY25Q3", "revenue": 1},
        {"symbol": "OK1", "fiscal_period": "FY25Q4", "revenue": 1},
        {"symbol": "OK1", "fiscal_period": "FY26Q1", "revenue": 1},
    ]

    def fake_load(tab, *, limit=500000):
        return {
            "company_master": masters,
            "financials_annual": annual,
            "financials_quarterly": quarterly,
            "share_count_history": [],
        }.get(tab, [])

    monkeypatch.setattr("financial_warehouse_completion.audit._load_rows", fake_load)
    q = queue_candidates(limit=50, include_thin=True, use_cache=False)
    assert q["ok"] is True
    symbols = [r["symbol"] for r in q["rows"]]
    assert symbols[0] == "EMPTY1"
    assert "ETF1" not in symbols
    assert q["counts"]["empty"] == 1
    assert q["counts"]["skipped_non_equity"] >= 1


def test_fill_company_uses_yahoo_backfill(monkeypatch):
    calls = {}

    def fake_backfill(symbol, *, actor="yahoo_fill", loader=None):
        calls["symbol"] = symbol
        return {"ok": True, "symbol": symbol, "annual_periods": 4, "quarterly_periods": 5}

    monkeypatch.setattr(
        "institutional_warehouse.backfill.statements.backfill_company",
        fake_backfill,
    )
    monkeypatch.setattr(
        "financial_warehouse_completion.share_count.sync_symbol",
        lambda symbol, actor="yahoo_fill": {"ok": True, "symbol": symbol, "written": 1},
    )
    monkeypatch.setattr(
        "financial_warehouse_completion.audit.company_audit",
        lambda symbol: {
            "classification": "PARTIAL",
            "annual": {"years": 4},
            "quarterly": {"quarters": 5},
        },
    )
    monkeypatch.setattr("financial_warehouse_completion.audit.clear_audit_cache", lambda: None)
    monkeypatch.setattr(
        "financial_warehouse_completion.yahoo_fill.clear_queue_cache",
        lambda: None,
    )

    out = fill_company("RELIANCE", actor="test")
    assert out["ok"] is True
    assert out["filled"] is True
    assert out["annual_periods"] == 4
    assert calls["symbol"] == "RELIANCE"
    assert out["source"] == "yahoo_finance_statements"


def test_run_batch_explicit_symbols(monkeypatch):
    monkeypatch.setattr(
        "financial_warehouse_completion.yahoo_fill.fill_company",
        lambda symbol, actor="yahoo_fill": {
            "ok": True,
            "filled": True,
            "symbol": symbol,
            "annual_periods": 3,
            "quarterly_periods": 4,
        },
    )
    out = run_batch(batch=2, symbols=["AAA", "BBB"], pause_seconds=0)
    assert out["ok"] is True
    assert out["batch"]["filled"] == 2
    assert out["vendor_historical_multiples"] is False


def test_status_surface():
    st = status()
    assert st["ok"] is True
    assert st["source"] == "yahoo_finance_statements"
    assert "runtime" in st
