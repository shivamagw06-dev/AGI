"""Upstox key-ratios normalisation + engine preference."""

from __future__ import annotations

from valuation_ratios.ingest import normalise_upstox_key_ratios
from valuation_engine import engine


UPSTOX_SAMPLE = {
    "status": "success",
    "data": [
        {"name": "P/E", "company_value": "20.15", "sector_value": "12.46"},
        {"name": "P/B", "company_value": "2.13", "sector_value": "1.53"},
        {"name": "ROA", "company_value": "4.39%", "sector_value": "7.54%"},
        {"name": "ROE", "company_value": "8.94%", "sector_value": "16.46%"},
        {"name": "ROCE", "company_value": "10.39%", "sector_value": "16.9%"},
        {"name": "EV/EBITDA", "company_value": "10.25", "sector_value": "6.94"},
    ],
}


def test_normalise_upstox_key_ratios_maps_all_six():
    rows = normalise_upstox_key_ratios({
        "symbol": "RELIANCE",
        "isin": "INE002A01018",
        "data": UPSTOX_SAMPLE["data"],
        "reported_date": "2026-08-04",
    })
    names = {r["ratio_name"] for r in rows}
    assert names == {"pe", "pb", "roa", "roe", "roce", "ev_ebitda"}
    pe = next(r for r in rows if r["ratio_name"] == "pe")
    assert pe["company_value"] == 20.15
    assert pe["sector_value"] == 12.46
    assert pe["provider"] == "upstox"
    assert pe["dqiv_status"] == "passed"
    assert pe["source"] == "upstox"


def test_percent_strings_parsed():
    rows = normalise_upstox_key_ratios({
        "symbol": "TCS",
        "isin": "INE467B01029",
        "data": [{"name": "ROE", "company_value": "45.2%", "sector_value": "20%"}],
    })
    assert len(rows) == 1
    assert rows[0]["company_value"] == 45.2


def test_engine_prefers_upstox_over_computed_pe():
    """When Upstox supplies PE, do not recompute from CMP/EPS."""
    record = {
        "ok": True,
        "symbol": "AAA",
        "latest_price": {"close": 100.0, "shares_outstanding": 1_000_000.0, "source": "nse"},
        "latest_annual": {
            "eps": 5.0, "book_value": 20.0, "revenue": 1000, "ebitda": 200,
            "debt": 0, "cash": 0, "equity": 500, "pat": 100, "source": "financial_connector",
        },
        "consensus": {},
        "provider_ratios": {
            "ok": True,
            "source": "upstox",
            "ratios": {
                "pe": {"company_value": 28.4, "sector_value": 24.7, "source": "upstox"},
                "pb": {"company_value": 3.1, "sector_value": 2.5, "source": "upstox"},
                "roe": {"company_value": 18.0, "sector_value": 14.0, "source": "upstox"},
                "ev_ebitda": {"company_value": 11.0, "sector_value": 9.0, "source": "upstox"},
            },
        },
    }
    values = engine.compute(record)
    # Computed PE would be 20 (100/5); provider wins.
    assert values["pe"].value == 28.4
    assert values["pe"].note == "provider"
    assert "upstox" in values["pe"].sources
    assert values["pb"].value == 3.1
    assert values["roe"].value == 18.0
    assert values["ev_ebitda"].value == 11.0
    # AGI still computes market cap from CMP × shares.
    assert values["market_cap"].value == 100_000_000.0


def test_schema_registers_valuation_ratios_tab():
    from institutional_warehouse.schema import tab

    t = tab("valuation_ratios")
    assert t.id == "valuation_ratios"
    assert t.mode == "append"
    keys = {c.key for c in t.columns}
    assert {"symbol", "isin", "ratio_name", "company_value", "sector_value", "snapshot_id"} <= keys


def test_fold_latest_ratio_rows_keeps_newest_per_symbol():
    from valuation_ratios.ingest import fold_latest_ratio_rows

    out = fold_latest_ratio_rows([
        {"symbol": "aaa", "ratio_name": "pe", "company_value": 10, "reported_date": "2026-08-20"},
        {"symbol": "AAA", "ratio_name": "pe", "company_value": 12.5, "reported_date": "2026-08-24",
         "sector_value": 18.0},
        {"symbol": "AAA", "ratio_name": "pb", "company_value": 2.1, "reported_date": "2026-08-24"},
        {"symbol": "BBB", "ratio_name": "roe", "company_value": 22, "reported_date": "2026-08-23"},
    ])
    assert out["AAA"]["pe"] == 12.5
    assert out["AAA"]["pe_sector"] == 18.0
    assert out["AAA"]["pb"] == 2.1
    assert out["AAA"]["as_of"] == "2026-08-24"
    assert out["BBB"]["roe"] == 22


def test_apply_latest_ratios_overlays_scanner_and_sector_fields():
    from valuation_ratios.ingest import apply_latest_ratios

    latest = {
        "INFY": {
            "pe": 22.5,
            "pb": 6.1,
            "roe": 31.0,
            "roce": 28.4,
            "ev_ebitda": 14.2,
            "as_of": "2026-08-24",
            "source": "warehouse.valuation_ratios",
        }
    }
    row = apply_latest_ratios({"ticker": "INFY", "pe": 18.0, "pb": 5.0}, latest=latest)
    assert row["pe"] == 22.5
    assert row["trailing_pe"] == 22.5
    assert row["pb"] == 6.1
    assert row["roe"] == 31.0
    assert row["roic"] == 28.4
    assert row["ev_ebitda"] == 14.2
    assert row["valuation_ratios_as_of"] == "2026-08-24"
