"""P2.6 Live Market Context — Phase 2.1 Sprint 1."""

from __future__ import annotations

from forecast_provider_integration.gateways.groww import GrowwMarketGateway
from live_market_context.production import analyse, health, package_for_ask_agi
from live_market_context.providers import is_contaminated_index_seed
from phase2_investment_intelligence.contract import validate_engine_payload
from phase2_investment_intelligence.milestones import IMPLEMENTATION_PR_CHECKLIST, milestones_board


def test_milestones_phase_2_1_active():
    board = milestones_board()
    assert board["active"] == "phase_2_1"
    assert board["milestones"][0]["workstreams"] == ["P2.6", "P2.3"]
    assert len(IMPLEMENTATION_PR_CHECKLIST) == 5
    assert "Did IAT still pass?" in IMPLEMENTATION_PR_CHECKLIST


def test_groww_fail_closed_no_nifty_seed_for_eternal():
    snap = GrowwMarketGateway().fetch_snapshot("ETERNAL", scope="company")
    # Must not attach NIFTY 24850 to ETERNAL
    assert snap.ltp != 24850.0
    assert snap.ltp is None or snap.entity == "ETERNAL"
    assert "NIFTY LTP" in (snap.note or "") or snap.ltp is None or snap.stale


def test_seeded_equity_still_works():
    snap = GrowwMarketGateway().fetch_snapshot("INFY", scope="company")
    assert snap.ltp is not None
    assert abs(float(snap.ltp) - 1582.4) < 0.1


def test_contamination_detector():
    assert is_contaminated_index_seed("ETERNAL", 24850.0) is True
    assert is_contaminated_index_seed("NIFTY", 24850.0) is False
    assert is_contaminated_index_seed("INFY", 1582.4) is False


def test_analyse_standard_contract(monkeypatch):
    # Force deterministic quote without network
    def _fake_quote(ticker, force=False):
        return {
            "ok": True,
            "ticker": ticker.upper(),
            "provider": "yahoo",
            "ltp": 311.8,
            "volume": 12_000_000,
            "relative_strength_52w": 0.64,
            "fifty_two_week_high": 368.45,
            "fifty_two_week_low": 212.6,
            "as_of": "2026-07-29T10:00:00Z",
            "age_sec": 30,
            "stale": False,
            "seeded": False,
            "lineage": [{"source": "yahoo_chart", "ref": "ETERNAL.NS"}],
        }

    monkeypatch.setattr("live_market_context.context.fetch_best_quote", _fake_quote)
    pack = analyse("ETERNAL", intrinsic_value=280.0)
    assert pack["engine"] == "live_market_context"
    assert pack["fabricated"] is False
    assert pack["failure_mode"]["block_unrelated_engines"] is False
    assert pack["panel"]["ltp"] == 311.8
    assert pack["panel"]["price_freshness"]["within_sla"] is True
    assert pack["panel"]["liquidity"]["band"] == "high"
    assert pack["panel"]["distance_to_intrinsic"]["available"] is True
    v = validate_engine_payload(pack)
    assert v["ok"] is True
    h = health()
    assert h["workstream_id"] == "P2.6"
    assert h["milestone"] == "phase_2_1"


def test_package_for_ask_agi_degrades_without_ticker():
    pack = package_for_ask_agi("market context?")
    assert pack["skipped"] is True
    assert pack["failure_mode"]["block_unrelated_engines"] is False
