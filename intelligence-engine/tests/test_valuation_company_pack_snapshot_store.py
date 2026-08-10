"""Unit tests for valuation company-pack snapshot helpers."""

from __future__ import annotations

import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from valuation_engine.snapshot_store import (  # noqa: E402
    build_data_quality,
    freshness_for_age,
    normalize_window,
)


def test_normalize_window():
    assert normalize_window("5y") == "5Y"
    assert normalize_window("MAX") == "MAX"
    assert normalize_window("nope") == "5Y"


def test_freshness_bands():
    assert freshness_for_age(0) == "fresh"
    assert freshness_for_age(20 * 60) == "aging"
    assert freshness_for_age(2 * 60 * 60) == "stale"


def test_build_data_quality_from_pack():
    payload = {
        "ok": True,
        "symbol": "TCS",
        "coverage": {"pct": 82.5},
        "health_score": {"score": 77, "band": "moderate"},
        "overview": {"data_quality": "moderate", "updated": "2026-08-10"},
        "data_quality": {
            "validated": True,
            "warnings": ["price lag"],
            "missing": ["ev_sales"],
            "conflicts": 1,
            "overrides": 0,
            "freshness": {
                "price_age_hours": 3.2,
                "ratio_age_hours": 8.0,
                "financial_age_hours": 40.0,
            },
        },
    }
    quality = build_data_quality(payload)
    assert quality["validated"] is True
    assert quality["warnings"] == 1
    assert quality["missing"] == 1
    assert quality["coverage_pct"] == 82.5
    assert quality["health_score"] == 77
    assert quality["price_age_hours"] == 3.2
