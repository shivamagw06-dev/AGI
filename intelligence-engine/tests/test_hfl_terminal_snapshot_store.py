"""Unit tests for Hedge Fund Lab terminal snapshot persistence helpers."""

from __future__ import annotations

import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from hedge_fund_lab.snapshot_store import (  # noqa: E402
    build_data_quality,
    flatten_opportunities,
    freshness_for_age,
)


def test_freshness_bands():
    assert freshness_for_age(0) == "fresh"
    assert freshness_for_age(14 * 60) == "fresh"
    assert freshness_for_age(20 * 60) == "aging"
    assert freshness_for_age(2 * 60 * 60) == "stale"


def test_build_data_quality_counts_cards():
    payload = {
        "ok": True,
        "hero": {
            "universe_scanned": 400,
            "live_opportunities": 7,
            "companies_flagged": 5,
        },
        "regime": {"stance": "risk_on", "universe": 400},
        "cards": [
            {"id": "value", "count": 3, "results": []},
            {"id": "growth", "count": 0, "results": []},
            {"id": "pairs", "count": 2, "results": []},
        ],
    }
    quality = build_data_quality(payload)
    assert quality["universe_scanned"] == 400
    assert quality["live_opportunities"] == 7
    assert quality["cards_with_results"] == 2
    assert quality["card_counts"]["value"] == 3
    assert quality["regime_stance"] == "risk_on"


def test_flatten_opportunities_includes_pairs_legs():
    payload = {
        "cards": [
            {
                "id": "value",
                "label": "Value",
                "results": [
                    {
                        "ticker": "axisbank",
                        "company_name": "Axis Bank",
                        "sector": "Banks",
                        "confidence": 72,
                        "why": "Cheap vs peers",
                    }
                ],
            },
            {
                "id": "pairs",
                "label": "Pairs",
                "results": [
                    {
                        "long_leg": {"ticker": "ultracemco", "company_name": "UltraTech", "sector": "Cement"},
                        "short_leg": {"ticker": "ambujacem", "company_name": "Ambuja"},
                        "confidence": 61,
                        "why": "Spread wide",
                    }
                ],
            },
        ]
    }
    rows = flatten_opportunities("snap-1", payload)
    assert len(rows) == 2
    assert rows[0]["ticker"] == "AXISBANK"
    assert rows[0]["scan_id"] == "value"
    assert rows[0]["rank"] == 1
    assert rows[1]["ticker"] == "ULTRACEMCO"
    assert rows[1]["scan_id"] == "pairs"
    assert rows[1]["row_payload"]["short_leg"]["ticker"] == "ambujacem"


def test_serve_terminal_overview_uses_snapshot_not_live_scan(monkeypatch):
    from hedge_fund_lab import snapshot_store as store

    monkeypatch.setattr(
        store,
        "latest_snapshot_row",
        lambda: {
            "generated_at": "2026-08-19T00:00:00Z",
            "freshness": "fresh",
            "payload": {
                "ok": True,
                "cards": [{"id": "quality", "results": [{"ticker": "SBIN", "confidence": 80}]}],
            },
        },
    )
    scanned = {"called": False}

    def _overview(**_kwargs):
        scanned["called"] = True
        return {"ok": True, "cards": []}

    monkeypatch.setattr("hedge_fund_lab.terminal.overview", _overview)
    out = store.serve_terminal_overview(limit=25)
    assert scanned["called"] is False
    assert out["cards"][0]["id"] == "quality"
    assert out["read_model"] == "supabase_hfl_terminal"


def test_serve_terminal_overview_warming_when_missing(monkeypatch):
    from hedge_fund_lab import snapshot_store as store

    monkeypatch.setattr(store, "latest_snapshot_row", lambda: None)
    out = store.serve_terminal_overview()
    assert out["status"] == "warming"
    assert out["cards"] == []
    assert out["ok"] is True
