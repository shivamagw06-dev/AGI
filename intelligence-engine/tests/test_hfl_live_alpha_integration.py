"""Live Alpha aggregation and Hedge Fund terminal integration tests."""

from __future__ import annotations

import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from hedge_fund_lab.live_alpha_bridge import (  # noqa: E402
    composite_score,
    confluence_label,
    engine_agreement,
    signed_score,
    unified_score,
)


def _signal(*, direction="positive", quality=72, alpha_z=1.2, liquidity_ok=True, label="strong"):
    return {
        "direction": direction,
        "alpha_z": alpha_z,
        "signal_quality_score": quality,
        "signal_quality_label": label,
        "liquidity_ok": liquidity_ok,
        "classification": "positive_research_candidate",
    }


def test_signed_score_respects_direction():
    assert signed_score(_signal(direction="positive")) > 0
    assert signed_score(_signal(direction="negative")) < 0
    assert signed_score(_signal(direction=None)) == 0


def test_engine_agreement_positive_mixed_negative():
    assert engine_agreement([_signal(direction="positive")]) == "single"
    assert engine_agreement([_signal(direction="positive"), _signal(direction="positive")]) == "positive"
    assert engine_agreement([_signal(direction="positive"), _signal(direction="negative")]) == "mixed"


def test_composite_score_aggregates_multiple_engines():
    active = [_signal(direction="positive", quality=80), _signal(direction="positive", quality=70)]
    score = composite_score(active)
    assert 0 < score <= 99


def test_confluence_labels():
    assert confluence_label(hfl_scanner_count=2, live_alpha_present=True, live_direction="positive", hfl_bias="positive") == "Confirmed"
    assert confluence_label(hfl_scanner_count=2, live_alpha_present=True, live_direction="negative", hfl_bias="positive") == "Timing conflict"
    assert confluence_label(hfl_scanner_count=0, live_alpha_present=True, live_direction="positive", hfl_bias=None) == "Tactical only"
    assert confluence_label(hfl_scanner_count=2, live_alpha_present=False, live_direction=None, hfl_bias="positive") == "Fundamental only"


def test_unified_score_penalizes_conflicts():
    aligned = unified_score(hfl_score=70, live_alpha_score=60, live_direction="positive", hfl_bias="positive")
    conflict = unified_score(hfl_score=70, live_alpha_score=60, live_direction="negative", hfl_bias="positive")
    assert conflict < aligned


def test_fetch_live_alpha_rows_without_supabase():
    from hedge_fund_lab.live_alpha_bridge import fetch_live_alpha_rows

    out = fetch_live_alpha_rows(limit=5)
    assert out["ok"] is False
    assert out["rows"] == []


def test_overview_requests_inventory_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("HEDGE_FUND_LAB_ROOT", str(tmp_path))
    from hedge_fund_lab import terminal as hfl_terminal

    seen: list[int] = []

    def fake_run_all(*, limit=12):
        seen.append(limit)
        empty = {k: [] for k in hfl_terminal._ORDER}
        return {"ok": True, "universe": [], "medians": {}, "results": empty}

    monkeypatch.setattr(hfl_terminal, "run_all", fake_run_all)
    monkeypatch.setattr(hfl_terminal, "regime", lambda universe=None: {"ok": True, "strategy_suitability": [], "universe": 0})
    monkeypatch.setattr(hfl_terminal, "market_dashboard", lambda universe=None, medians=None: {"ok": True})
    monkeypatch.setattr(hfl_terminal, "factor_dashboard", lambda universe=None, medians=None: {"ok": True, "factors": []})
    monkeypatch.setattr(hfl_terminal, "fetch_live_alpha_rows", lambda limit=200: {"ok": False, "rows": [], "meta": {}})

    payload = hfl_terminal._overview_uncached(12, "limit:12", 0.0)
    assert payload["ok"] is True
    assert seen[0] == hfl_terminal._INVENTORY_LIMIT
