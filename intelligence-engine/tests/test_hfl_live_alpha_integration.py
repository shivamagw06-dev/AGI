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
    effective_agreement,
    engine_agreement,
    fundamental_bias,
    live_alpha_confirms,
    live_alpha_conflicts,
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


def test_fundamental_bias_and_effective_agreement():
    assert fundamental_bias(60) == "positive"
    assert fundamental_bias(40) == "negative"
    assert fundamental_bias(50) is None
    assert effective_agreement(fundamental_count=1, live_alpha_confirms=False) == 1
    assert effective_agreement(fundamental_count=1, live_alpha_confirms=True) == 2
    assert live_alpha_confirms(hfl_bias="positive", live_direction="positive") is True
    assert live_alpha_conflicts(hfl_bias="positive", live_direction="negative") is True


def test_conflict_does_not_inflate_agreement():
    """One fundamental + conflicting Live Alpha must not reach agreement=2."""
    fund_n = 1
    confirms = live_alpha_confirms(hfl_bias="positive", live_direction="negative")
    assert confirms is False
    assert effective_agreement(fundamental_count=fund_n, live_alpha_confirms=confirms) == 1


def test_newest_neutral_blocks_older_qualifying(monkeypatch):
    from hedge_fund_lab import live_alpha_bridge as bridge

    runs = [{"id": "run-new", "engine": "cross_sectional_momentum_v1", "as_of": "2026-08-10T10:00:00Z"}]
    signals = [
        {
            "symbol": "TCS",
            "sector": "IT",
            "run_id": "run-new",
            "direction": None,
            "alpha_z": 0.5,
            "signal_quality_score": 80,
            "signal_quality_label": "strong",
            "liquidity_ok": True,
            "classification": "neutral",
            "factor_values": {},
            "created_at": "2026-08-10T10:00:00Z",
        },
        {
            "symbol": "TCS",
            "sector": "IT",
            "run_id": "run-new",
            "direction": "positive",
            "alpha_z": 1.5,
            "signal_quality_score": 80,
            "signal_quality_label": "strong",
            "liquidity_ok": True,
            "classification": "positive_research_candidate",
            "factor_values": {},
            "created_at": "2026-08-10T09:00:00Z",
        },
    ]

    def fake_rest(path, **kwargs):
        if path.startswith("live_alpha_runs"):
            return runs
        if path.startswith("live_alpha_signals"):
            return signals
        return None

    monkeypatch.setattr(bridge, "_rest", fake_rest)
    monkeypatch.setattr(bridge, "_signal_is_fresh", lambda signal, as_of=None: True)
    out = bridge.fetch_live_alpha_rows(limit=10)
    assert out["ok"] is True
    assert out["rows"] == []


def test_next_session_open_keeps_closing_signal_through_evening():
    from datetime import datetime, timedelta, timezone

    from hedge_fund_lab.live_alpha_bridge import _next_nse_session_open

    # ~3:25 PM IST on a Monday
    closing = datetime(2026, 8, 10, 9, 55, tzinfo=timezone.utc)
    nxt = _next_nse_session_open(closing)
    assert nxt > closing
    # A fixed 120-minute window would expire before the evening research window ends.
    assert closing + timedelta(minutes=120) < nxt


def test_fetch_live_alpha_rows_without_supabase():
    from hedge_fund_lab.live_alpha_bridge import fetch_live_alpha_rows

    out = fetch_live_alpha_rows(limit=5)
    assert out["ok"] is False
    assert out["rows"] == []


def test_live_alpha_desk_drops_single_engine(monkeypatch):
    from hedge_fund_lab import terminal as hfl

    monkeypatch.setattr(
        hfl,
        "fetch_live_alpha_rows",
        lambda limit=200: {
            "ok": True,
            "rows": [
                {"ticker": "NOISE", "engine_count": 1, "company_name": "NOISE", "live_alpha_score": 90},
                {"ticker": "TCS", "engine_count": 2, "company_name": "TCS", "live_alpha_score": 40},
            ],
        },
    )
    monkeypatch.setattr(
        "hedge_fund_lab.live_prices.overlay_live_prices_on_payload",
        lambda rows, latest=None: rows,
    )
    rows = hfl._scan_live_alpha(
        [{"ticker": "TCS", "company_name": "Tata Consultancy Services"}],
        {},
        10,
    )
    assert [row["ticker"] for row in rows] == ["TCS"]
    assert rows[0]["company_name"] == "Tata Consultancy Services"


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
