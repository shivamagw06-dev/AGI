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
