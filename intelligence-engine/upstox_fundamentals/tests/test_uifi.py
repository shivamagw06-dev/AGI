"""UIFI normaliser + ingest contract tests."""

from __future__ import annotations

from upstox_fundamentals import health
from upstox_fundamentals.normalize import (
    merge_statement_rows,
    normalise_competitors,
    normalise_corporate_actions,
    normalise_profile,
    normalise_shareholding,
    normalise_statements,
)


def test_health_contract():
    h = health()
    assert h["ok"] is True
    assert h["engine"] == "UIFI"
    assert "profile" in h["datasets"]
    assert h["rule"] == "products_read_warehouse_only"


def test_normalise_profile():
    row = normalise_profile({
        "symbol": "INFY",
        "isin": "INE009A01021",
        "data": {
            "company_name": "Infosys Ltd",
            "sector": "Information Technology",
            "industry": "IT Services",
            "website": "https://www.infosys.com",
            "business_description": "IT services",
            "employee_count": 250000,
        },
    })
    assert row["symbol"] == "INFY"
    assert row["instrument_key"] == "NSE_EQ|INE009A01021"
    assert row["sector"] == "Information Technology"
    assert row["dqiv_status"] == "passed"


def test_normalise_profile_documented_upstox_shape():
    row = normalise_profile({
        "symbol": "RELIANCE",
        "isin": "INE002A01018",
        "data": {
            "company_profile": "Diversified energy, retail and digital services business.",
            "sector": "Refineries",
            "sector_market_cap_inr": {"value": 1942866.05, "unit": "crore"},
            "sector_market_cap_usd": {"value": 215.87, "unit": "billion"},
        },
    })
    assert row["business_description"].startswith("Diversified energy")
    assert row["sector_market_cap_inr"] == 1942866.05
    assert row["sector_market_cap_usd"] == 215.87
    assert row.get("market_cap_inr") is None


def test_normalise_income_statement_periods():
    rows = normalise_statements({
        "symbol": "INFY",
        "data": {
            "units_in": "crore",
            "statement_type": "Consolidated",
            "Revenue": {"FY2024": 150000, "FY2023": 140000},
            "PAT": {"FY2024": 25000, "FY2023": 23000},
            "EPS": {"FY2024": 60.5, "FY2023": 55.1},
        },
    }, kind="income-statement")
    assert len(rows) >= 2
    assert {r["fiscal_year"] for r in rows} >= {"FY2024", "FY2023"}
    assert all(r["statement_type"] == "CONSOLIDATED" for r in rows)
    assert any(r.get("revenue") == 150000 for r in rows)


def test_normalise_upstox_v2_history_shape():
    """Upstox docs shape: category/history + full_statement with Mar YYYY periods."""
    rows = normalise_statements({
        "symbol": "RELIANCE",
        "data": {
            "type": "consolidated",
            "time_period": "yearly",
            "units_in": "crore",
            "income_statement": [
                {
                    "category": "revenue",
                    "history": [
                        {"value": 982671, "period": "Mar 2025"},
                        {"value": 917121, "period": "Mar 2024"},
                    ],
                },
                {
                    "category": "net_profit",
                    "history": [
                        {"value": 80787, "period": "Mar 2025"},
                        {"value": 78633, "period": "Mar 2024"},
                    ],
                },
            ],
            "full_statement": [
                {
                    "particular": "Total Revenue",
                    "history": [
                        {"period": "Mar 2025", "value": 982671},
                        {"period": "Mar 2024", "value": 917121},
                    ],
                },
                {
                    "particular": "Profit After Tax",
                    "history": [
                        {"period": "Mar 2025", "value": 80787},
                        {"period": "Mar 2024", "value": 78633},
                    ],
                },
                {
                    "particular": "EPS - Basic",
                    "history": [
                        {"period": "Mar 2025", "value": 51.47},
                        {"period": "Mar 2024", "value": 51.45},
                    ],
                },
            ],
        },
    }, kind="income-statement")
    assert len(rows) >= 2
    assert all(r["statement_frequency"] == "ANNUAL" for r in rows)
    assert all(r["statement_type"] == "CONSOLIDATED" for r in rows)
    assert {r["fiscal_year"] for r in rows} >= {"FY2025", "FY2024"}
    fy25 = next(r for r in rows if r["fiscal_year"] == "FY2025")
    assert fy25.get("revenue") == 982671
    assert fy25.get("pat") == 80787
    assert fy25.get("eps") == 51.47


def test_merge_statements():
    income = normalise_statements({
        "symbol": "TCS",
        "data": {"units_in": "crore", "Revenue": {"FY2024": 200000}, "PAT": {"FY2024": 40000}},
    }, kind="income-statement")
    balance = normalise_statements({
        "symbol": "TCS",
        "data": {
            "units_in": "crore",
            "Total Assets": {"FY2024": 180000},
            "Shareholders Equity": {"FY2024": 120000},
        },
    }, kind="balance-sheet")
    cash = normalise_statements({
        "symbol": "TCS",
        "data": {
            "units_in": "crore",
            "Operating Cash Flow": {"FY2024": 45000},
            "Capex": {"FY2024": 5000},
        },
    }, kind="cash-flow")
    merged = merge_statement_rows(income + balance + cash)
    assert len(merged) == 1
    row = merged[0]
    assert row.get("revenue") == 200000
    assert row.get("assets") == 180000
    assert row.get("cfo") == 45000


def test_shareholding_dqiv():
    rows = normalise_shareholding({
        "symbol": "INFY",
        "data": [{
            "date": "2026-03-31",
            "promoter": 14.5,
            "fii": 33.0,
            "dii": 28.0,
            "public": 24.5,
        }],
    })
    assert len(rows) == 1
    assert rows[0]["promoter_holding"] == 14.5
    assert rows[0]["institutional_holding"] == 61.0


def test_shareholding_documented_category_history_shape():
    rows = normalise_shareholding({
        "symbol": "RELIANCE",
        "data": [
            {"category": "promoters", "history": [{"period": "Mar 2026", "value": 50}]},
            {"category": "fii", "history": [{"period": "Mar 2026", "value": 20}]},
            {"category": "other_dii", "history": [{"period": "Mar 2026", "value": 10}]},
            {"category": "mutual_funds", "history": [{"period": "Mar 2026", "value": 5}]},
            {"category": "retail_and_other", "history": [{"period": "Mar 2026", "value": 15}]},
        ],
    })
    assert len(rows) == 1
    assert rows[0]["as_of"] == "2026-03-31"
    assert rows[0]["dii"] == 15
    assert rows[0]["institutional_holding"] == 35


def test_corporate_actions_secondary_confidence():
    rows = normalise_corporate_actions({
        "symbol": "INFY",
        "data": [{
            "name": "Dividend",
            "amount": 20,
            "expiry_date": "2026-06-01",
            "event_details": [
                {"name": "Announcement date", "value": "2026-04-15"},
                {"name": "Ex dividend date", "value": "2026-06-01"},
            ],
        }],
    })
    assert rows
    assert rows[0]["confidence"] == 0.55
    assert rows[0]["action_type"] == "dividend"
    assert rows[0]["source"] == "upstox"


def test_corporate_actions_parses_documented_human_dates():
    rows = normalise_corporate_actions({
        "symbol": "RELIANCE",
        "data": [{
            "name": "Dividend",
            "amount": 5.5,
            "expiry_date": "14 Aug 2025",
            "event_details": [
                {"name": "Announcement date", "value": "25 Apr 2025"},
                {"name": "Ex dividend date", "value": "14 Aug 2025"},
            ],
        }],
    })
    assert rows[0]["action_date"] == "2025-08-14"
    assert rows[0]["announcement_date"] == "2025-04-25"


def test_competitors_no_self():
    rows = normalise_competitors({
        "symbol": "INFY",
        "isin_map": {"INE467B01029": "TCS", "INE009A01021": "INFY"},
        "data": ["NSE_EQ|INE467B01029", "NSE_EQ|INE009A01021"],
    })
    assert len(rows) == 1
    assert rows[0]["peer_symbol"] == "TCS"
    assert rows[0]["relationship"] == "related"
    assert rows[0]["confidence"] == 0.6


def test_ingest_bundle_profile(monkeypatch):
    from upstox_fundamentals import ingest

    writes = []

    class GW:
        def write(self, tab, rows, **kwargs):
            writes.append({"tab": tab, "rows": rows, **kwargs})
            return {"ok": True, "written": len(rows)}

    import institutional_warehouse.gateway as gateway_mod
    import institutional_warehouse.store as store_mod
    monkeypatch.setattr(gateway_mod, "write", GW().write)
    monkeypatch.setattr(store_mod, "all_rows", lambda *_, **__: [])

    out = ingest.ingest_bundle({
        "dataset": "profile",
        "companies": [{
            "symbol": "INFY",
            "isin": "INE009A01021",
            "data": {"company_name": "Infosys", "sector": "IT", "industry": "Services"},
        }],
    })
    assert out["ok"] is True
    tabs = {w["tab"] for w in writes}
    assert "company_master" in tabs
    assert "profile_history" in tabs


def test_upstox_profile_does_not_overwrite_existing_capiq_master(monkeypatch):
    from upstox_fundamentals import ingest
    import institutional_warehouse.gateway as gateway_mod
    import institutional_warehouse.store as store_mod

    writes = []
    monkeypatch.setattr(store_mod, "all_rows", lambda tab, **_: [{
        "company_id": "RELIANCE",
        "symbol": "RELIANCE",
        "company_name": "Reliance Industries Limited",
        "isin": "INE002A01018",
        "instrument_key": "NSE_EQ|INE002A01018",
        "sector": "Diversified",
        "industry": "Conglomerate",
        "business_description": "Canonical CapIQ description",
        "source": "capital_iq",
    }] if tab == "company_master" else [])
    monkeypatch.setattr(gateway_mod, "write", lambda tab, rows, **kwargs: (
        writes.append((tab, rows, kwargs)) or {"ok": True, "written": len(rows)}
    ))

    out = ingest.ingest_profile(normalise_profile({
        "symbol": "RELIANCE",
        "isin": "INE002A01018",
        "data": {"sector": "Refineries", "company_profile": "Provider description"},
    }))
    assert out["company_master"]["written"] == 0
    assert [tab for tab, _, _ in writes] == ["profile_history"]


def test_upstox_statements_skip_matching_capiq_period(monkeypatch):
    from upstox_fundamentals import ingest
    import institutional_warehouse.gateway as gateway_mod
    import institutional_warehouse.store as store_mod

    writes = []
    monkeypatch.setattr(store_mod, "all_rows", lambda tab, **_: [{
        "symbol": "RELIANCE",
        "statement_type": "CONSOLIDATED",
        "fiscal_year": "FY2025",
        "source": "capital_iq",
    }] if tab == "financials_annual" else [])
    monkeypatch.setattr(gateway_mod, "write", lambda tab, rows, **kwargs: (
        writes.append((tab, rows)) or {"ok": True, "written": len(rows)}
    ))

    out = ingest.ingest_statements([{
        "symbol": "RELIANCE",
        "statement_type": "CONSOLIDATED",
        "statement_frequency": "ANNUAL",
        "fiscal_year": "FY2025",
        "revenue": 100,
    }])
    assert out["capiq_rows_preserved"] == 1
    assert not writes
