"""Unit tests for Phase 3.4 Research Intelligence."""

from __future__ import annotations

from research_intelligence.corpus import get_corpus, list_entities
from research_intelligence.production import analyse, health, soft_slice_for_ask_agi
from research_intelligence.schema import ASK_WIRED, KNOWLEDGE_AUTHORITY, RECOMMENDATION_POLICY


def test_health_wired_via_kul():
    h = health()
    assert h["ok"] is True
    assert h["ask_wired"] is True
    assert ASK_WIRED is True
    assert h["ask_wired_via"] == "knowledge_unification.providers.research_intelligence"
    assert h["entity_count"] >= 5
    assert h["knowledge_authority"] == KNOWLEDGE_AUTHORITY


def test_soft_slice_diagnostics_only():
    out = soft_slice_for_ask_agi("How has management guidance evolved for TCS?")
    assert out.get("ask_wired") is True
    assert out.get("ask_wired_via") == "knowledge_unification.providers.research_intelligence"
    assert out.get("found") is True


def test_executive_note_order():
    out = analyse("Provide an executive research note for Reliance.", entity="reliance")
    assert out["ok"] is True
    assert out["recommendation"] is None
    assert out["recommendation_policy"] == RECOMMENDATION_POLICY
    assert out["executive_summary"]
    assert out["whats_new"]
    assert out["business_impact"]
    assert out["financial_impact"]
    assert out["industry_impact"]
    assert out["investment_implications"]
    assert out["evidence"]
    assert out["unknowns"]
    assert out["monitoring_points"]
    assert out["executive_note_order"][0] == "executive_summary"


def test_deep_research_no_reco():
    out = analyse("Summarize five years of capital allocation for TCS.", entity="tcs")
    assert out["ok"] is True
    assert out.get("deep_research")
    assert "buy" not in (out.get("summary") or "").lower() or "no buy" in (out.get("summary") or "").lower()


def test_knowledge_authority():
    out = analyse("Explain knowledge evolution from research to portfolio for Infosys.", entity="infosys")
    assert out.get("knowledge_authority") == KNOWLEDGE_AUTHORITY
    assert "consume" in (out.get("summary") or "").lower() or "authority" in (out.get("summary") or "").lower()


def test_corpus():
    assert "reliance" in list_entities()
    c = get_corpus("reliance")
    assert c and len(c["annual_reports"]) >= 3


def test_refuse_forecast():
    out = analyse("What will Reliance report next quarter?", entity="reliance")
    assert out.get("policy_refuse") is True
    assert "refuse_forecast" in (out.get("modules_used") or [])
    assert out.get("recommendation") is None


def test_refuse_recommendation():
    out = analyse("BUY or SELL Reliance?", entity="reliance")
    assert out.get("policy_refuse") is True
    assert "refuse_recommendation" in (out.get("modules_used") or [])
    assert out.get("recommendation") is None


def test_estimate_meta_not_refused():
    out = analyse(
        "Explain why estimate intelligence for TCS does not forecast.",
        entity="tcs",
    )
    assert out.get("policy_refuse") is not True
    assert "estimates" in (out.get("modules_used") or [])
