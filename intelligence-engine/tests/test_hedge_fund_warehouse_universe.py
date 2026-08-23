"""Hedge Fund Strategy Lab reads the warehouse / Market Intelligence universe."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))


@pytest.fixture
def warehouse_universe(monkeypatch):
    mi_rows = [
        {
            "symbol": "AAA",
            "company_name": "Alpha Industries",
            "sector": "Industrials",
            "industry": "Capital Goods",
            "industry_dna": "capital_goods",
            "market_cap": 5e11,
            "cmp": 100.0,
            "pe": 12.0,
            "pb": 1.5,
            "ev_ebitda": 8.0,
            "roe": 22.0,
            "dividend_yield": 1.2,
            "consensus_target": 120.0,
            "consensus_upside": 20.0,
            "analyst_count": 15,
            "source": "upstox",
        },
        {
            "symbol": "BBB",
            "company_name": "Beta Soft",
            "sector": "Information Technology",
            "industry": "IT Services",
            "industry_dna": "it_services",
            "market_cap": 8e11,
            "cmp": 200.0,
            "pe": 28.0,
            "pb": 6.0,
            "ev_ebitda": 18.0,
            "roe": 30.0,
            "dividend_yield": 0.8,
            "consensus_target": 210.0,
            "consensus_upside": 5.0,
            "analyst_count": 22,
            "source": "upstox",
        },
    ]

    monkeypatch.setattr(
        "market_intelligence_engine.universe.load_universe",
        lambda limit=5000: {
            "ok": True,
            "valuation_date": "2026-08-04",
            "rows": mi_rows,
        },
    )

    class _Store:
        @staticmethod
        def all_rows(tab, limit=1000):
            if tab == "historical_ratios":
                return [
                    {
                        "symbol": "AAA",
                        "period": "FY25",
                        "basis": "annual",
                        "roe": 22.0,
                        "net_margin": 14.0,
                        "debt_equity": 0.4,
                    },
                    {
                        "symbol": "BBB",
                        "period": "FY25",
                        "basis": "annual",
                        "roe": 30.0,
                        "net_margin": 18.0,
                        "debt_equity": 0.1,
                    },
                ]
            if tab == "hedge_fund_factors":
                return [
                    {
                        "symbol": "AAA",
                        "as_of": "2026-08-04",
                        "value_score": 72.0,
                        "quality_score": 80.0,
                        "growth_score": 70.0,
                        "momentum_score": 76.0,
                        "technical_score": 78.0,
                        "trend_score": 75.0,
                        "momentum_12_1_pct": 18.5,
                        "volume_ratio_20d": 1.3,
                        "consensus_score": 60.0,
                        "opportunity_score": 75.0,
                        "strategy_agreement": 3,
                    }
                ]
            if tab == "consensus":
                return [
                    {
                        "symbol": "AAA",
                        "consensus_date": "2026-08-04",
                        "buy": 10,
                        "analyst_count": 15,
                        "target_price": 120.0,
                    },
                    {
                        "symbol": "BBB",
                        "consensus_date": "2026-08-04",
                        "buy": 14,
                        "analyst_count": 22,
                        "target_price": 210.0,
                    },
                ]
            if tab == "daily_market_history":
                # ~1y of sparse points for AAA: +50%
                rows = []
                for i in range(260):
                    rows.append({"symbol": "AAA", "date": f"2025-{(i % 12) + 1:02d}-01", "close": 100.0})
                rows.append({"symbol": "AAA", "date": "2026-08-04", "close": 150.0})
                return rows
            return []

        @staticmethod
        def fetch(tab, filters=None, limit=1000):
            if tab == "historical_valuation":
                return {
                    "rows": [
                        {"symbol": "AAA", "date": "2026-08-04", "forward_pe": 10.0},
                        {"symbol": "BBB", "date": "2026-08-04", "forward_pe": 24.0},
                    ]
                }
            return {"rows": []}

    monkeypatch.setattr("institutional_warehouse.store.all_rows", _Store.all_rows)
    monkeypatch.setattr("institutional_warehouse.store.fetch", _Store.fetch)
    monkeypatch.setattr(
        "hedge_fund_lab.scanner._legacy_consensus",
        lambda ticker: {},
    )
    # These tests assert source construction, not asynchronous cache timing.
    # Production _universe() may intentionally return a previous snapshot while
    # refreshing; route the fixture through the deterministic builder.
    from hedge_fund_lab import scanner as hfl_scanner
    monkeypatch.setattr(hfl_scanner, "_universe", hfl_scanner._build_universe)
    return mi_rows


def test_universe_prefers_warehouse(warehouse_universe):
    from hedge_fund_lab.scanner import SOURCES, _universe, universe_meta

    rows = _universe()
    assert len(rows) == 2
    by_tk = {r["ticker"]: r for r in rows}
    assert by_tk["AAA"]["primary_sector"] == "Industrials"
    assert by_tk["AAA"]["profit_margin"] == pytest.approx(14.0)
    assert by_tk["AAA"]["debt_to_equity"] == pytest.approx(40.0)  # 0.4 × 100
    assert by_tk["AAA"]["consensus"]["upside"] == pytest.approx(20.0)
    assert by_tk["AAA"]["consensus"]["buy_count"] == pytest.approx(10)
    assert by_tk["AAA"]["forward_pe"] == pytest.approx(10.0)
    assert by_tk["AAA"]["factors"]["opportunity_score"] == pytest.approx(75.0)
    assert by_tk["AAA"]["consensus"]["return_1y"] is not None

    meta = universe_meta()
    assert meta["source"] == "warehouse+market_intelligence"
    assert meta["as_of"] == "2026-08-04"
    assert meta["count"] == 2
    assert meta["factors_joined"] == 1
    assert SOURCES["market_data"].startswith("warehouse")


def test_scan_sources_are_warehouse(warehouse_universe):
    from hedge_fund_lab.scanner import scan

    out = scan("quality", limit=5)
    assert out["ok"] is True
    assert out["sources"]["consensus"] == "warehouse.consensus"
    assert out["universe_meta"]["source"] == "warehouse+market_intelligence"


def test_alpha_uses_fundamentals_and_technical_screen_is_paused(warehouse_universe):
    from hedge_fund_lab.scanner import scan

    alpha = scan("alpha", limit=5)
    technical = scan("technical", limit=5)

    assert alpha["ok"] is True
    assert alpha["count"] == 1
    assert alpha["results"][0]["ticker"] == "AAA"
    assert alpha["results"][0]["factor_agreement"] >= 3
    assert set(alpha["results"][0]["factor_scores"]) == {"value", "quality", "growth", "consensus"}
    assert technical["ok"] is False
    assert technical["error"] == "technical_research_paused"


def test_health_reports_live_feed(warehouse_universe):
    from hedge_fund_lab.production import health

    h = health()
    assert h["ok"] is True
    assert h["live_feed"] is True
    assert h["universe"]["count"] == 2


def test_record_daily_snapshot(warehouse_universe, tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_FUND_LAB_ROOT", str(tmp_path))
    from hedge_fund_lab.terminal import record_daily_snapshot

    out = record_daily_snapshot(limit=10)
    assert out["ok"] is True
    assert out["universe_scanned"] == 2
    assert (tmp_path / "snapshots.json").exists()


def test_legacy_fallback_when_warehouse_empty(monkeypatch):
    from hedge_fund_lab import scanner as hfl_scanner

    monkeypatch.setattr(
        hfl_scanner,
        "_universe_from_warehouse",
        lambda: [],
    )

    def _fake_legacy():
        hfl_scanner._UNIVERSE_META.update(
            {
                "source": "legacy_valuation_terminal",
                "as_of": None,
                "count": 1,
                "factors_joined": 0,
            }
        )
        return [
            {
                "ticker": "LEGACY",
                "company_name": "Legacy Co",
                "primary_sector": "Energy",
                "primary_industry": "Oil",
                "pe": 9.0,
                "consensus": {},
            }
        ]

    monkeypatch.setattr(hfl_scanner, "_universe_from_legacy", _fake_legacy)
    # Exercise the source fallback directly. _universe() is intentionally an
    # asynchronous snapshot cache and may return an earlier valid snapshot.
    rows = hfl_scanner._build_universe()
    assert rows[0]["ticker"] == "LEGACY"
    assert hfl_scanner.universe_meta()["source"] == "legacy_valuation_terminal"
