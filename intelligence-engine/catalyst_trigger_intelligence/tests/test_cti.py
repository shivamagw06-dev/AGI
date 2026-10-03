"""Sprint 9.3 — Catalyst & Trigger Intelligence tests."""

from __future__ import annotations

from catalyst_trigger_intelligence.catalysts import company_catalysts, market_catalysts, sector_catalysts
from catalyst_trigger_intelligence.evaluation import evaluate_company, evaluate_trigger, trigger_matrix_report
from catalyst_trigger_intelligence.monitoring import monitoring_pack
from catalyst_trigger_intelligence.production import dashboard, health
from catalyst_trigger_intelligence.schema import PRIMARY_QUESTION, TRIGGER_STATES
from catalyst_trigger_intelligence.store import get_store
from catalyst_trigger_intelligence.traces import clear as clear_traces
from catalyst_trigger_intelligence.triggers import build_company_triggers


def setup_function() -> None:
    get_store().clear()
    clear_traces()


def test_health_and_primary_question() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["primary_question"] == PRIMARY_QUESTION
    assert h["does_not_forecast"] is True
    assert h["auto_rewrites_thesis"] is False
    assert list(TRIGGER_STATES)[0] == "Scheduled"


def test_infosys_company_catalysts_cover_categories() -> None:
    pack = company_catalysts("INFY")
    assert pack["ticker"] == "INFY"
    assert pack["sector"] == "it_services"
    assert pack["does_not_forecast"] is True
    ids = {c["id"] for c in pack["company"]}
    assert "quarterly_earnings" in ids
    assert "large_deal_wins" in ids
    assert pack["sector_catalysts"]
    assert pack["macro_catalysts"]
    assert any(c["id"] == "ai_spending" for c in pack["sector_catalysts"])


def test_sector_and_market_catalysts() -> None:
    banks = sector_catalysts("banks")
    assert banks["count"] >= 1
    assert any(i["id"] == "credit_growth_cycle" for i in banks["items"])
    market = market_catalysts()
    assert any(i["id"] == "rbi_policy" for i in market["macro"])
    assert any(i["id"] == "fii_flows" for i in market["market"])
    rbi = next(i for i in market["macro"] if i["id"] == "rbi_policy")
    assert "25bps" in rbi["condition"]
    assert rbi["priority"] == "Critical"


def test_triggers_have_lifecycle_and_institutional_rule() -> None:
    pack = build_company_triggers("INFY", persist=True)
    assert pack["count"] >= 5
    assert pack["auto_rewrites_thesis"] is False
    assert "Base Case unless" in pack["institutional_rule"]
    tr = pack["triggers"][0]
    assert tr["state"] in TRIGGER_STATES
    assert tr["condition"]
    assert tr["affected_scenario"]
    assert tr["monitoring_source"]
    assert tr["auto_rewrites_thesis"] is False
    stored = get_store().list_for_entity("INFY")
    assert len(stored) >= 5


def test_strong_earnings_strengthens_bull_without_thesis_rewrite() -> None:
    pack = build_company_triggers("INFY", persist=True)
    earnings = next(t for t in pack["triggers"] if t.get("catalyst_id") == "quarterly_earnings")
    result = evaluate_trigger(
        earnings["trigger_id"],
        observation={"metrics": {"revenue_growth": 0.18}},
        confirm=True,
        apply=True,
    )
    assert result["condition_met"] is True
    assert result["state"] == "Applied"
    assert result["auto_rewrites_thesis"] is False
    assessment = result["scenario_assessment"]
    assert assessment["scenario_states"]["bull"] == "Strengthened"
    assert assessment["thesis_auto_updated"] is False
    assert assessment["governance_auto_updated"] is False


def test_rbi_cut_trigger_for_banks() -> None:
    pack = build_company_triggers("HDFCBANK", persist=True)
    rbi = next((t for t in pack["triggers"] if t.get("catalyst_id") == "rbi_policy"), None)
    assert rbi is not None
    assert "25bps" in (rbi.get("condition") or "")
    result = evaluate_trigger(
        rbi["trigger_id"],
        observation={"metrics": {"rate_cut_bps": 25}},
        confirm=True,
    )
    assert result["condition_met"] is True
    assert result["scenario_assessment"]["scenario_states"]["bull"] == "Strengthened"


def test_trigger_matrix_and_monitoring_pack() -> None:
    build_company_triggers("INFY", persist=True)
    evaluate_company(
        "INFY",
        observations={"quarterly_earnings": {"metrics": {"revenue_growth": 0.16}}},
        auto_confirm=True,
    )
    report = trigger_matrix_report("INFY")
    assert report["count"] >= 1
    assert report["matrix"]
    mon = monitoring_pack(
        "INFY",
        observations={"quarterly_earnings": {"metrics": {"revenue_growth": 0.16}}},
    )
    assert mon["mutates_thesis"] is False
    assert mon["active_triggers"] is not None
    assert mon["upcoming_catalysts"]


def test_mission_control_dashboard() -> None:
    d = dashboard()
    assert d["primary_question"] == PRIMARY_QUESTION
    assert "upcoming_catalysts" in d
    assert "trigger_status_counts" in d
    assert d["freeze_locks"]["does_not_auto_rewrite_thesis"] is True
