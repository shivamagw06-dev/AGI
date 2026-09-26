"""Institutional Playbook Framework v1.0 tests."""

from __future__ import annotations

from answer_construction.response_constitution import apply_response_constitution
from institutional_playbook_framework import apply_institutional_playbook_framework, health, resolve_playbook


def test_health():
    h = health()
    assert h["status"] == "ok"
    assert h["deterministic"] is True
    assert h["playbook_count"] >= 30


def test_resolve_buy_question():
    r = resolve_playbook("Should I buy TCS?", irl_intent="Analyse")
    assert r["playbook_key"] == "investment_assessment"
    assert "Company Intelligence" in r["required_intelligence"]


def test_resolve_valuation_question():
    r = resolve_playbook("Is Reliance expensive?", irl_intent="Valuation")
    assert r["playbook_key"] == "valuation_assessment"


def test_resolve_peer_comparison():
    r = resolve_playbook("Compare HDFC Bank vs ICICI Bank", irl_intent="Compare")
    assert r["playbook_key"] == "peer_comparison"


def test_journey_progress():
    base = apply_response_constitution(
        {
            "executive": "TCS remains a leading IT services franchise.",
            "thesis": "Scale supports research interest.",
            "house_label": "Constructive",
            "bull": ["Client retention"],
            "bear": ["Wage inflation"],
        },
        query="Should I buy TCS?",
        ticker="TCS",
        company="Tata Consultancy Services",
        confidence=72,
    )
    out = apply_institutional_playbook_framework(
        base,
        query="Should I buy TCS?",
        ticker="TCS",
        intent_resolution={"intent": "Analyse"},
    )
    ipf = out["institutional_playbook_framework"]
    assert ipf["enabled"] is True
    journey = out["research_journey"]
    assert journey["progress_pct"] >= 0
    assert len(journey["steps"]) >= 5
    assert out["suggested_next_research"]


def test_journey_advances_with_memory():
    state = {"completed_steps": ["Business Quality", "Financial Quality"], "turn_count": 2}
    out = apply_institutional_playbook_framework(
        {"executive": "Valuation review", "response_constitution": {"direct_answer": "Valuation elevated"}},
        query="Is TCS expensive?",
        ticker="TCS",
        intent_resolution={"intent": "Valuation"},
        research_journey_state=state,
    )
    completed = out["research_journey_state"]["completed_steps"]
    assert "Valuation" in completed
    assert out["research_journey"]["next_step"]


def test_no_forbidden_language_in_validation():
    out = apply_institutional_playbook_framework(
        {"executive": "You must buy this stock now.", "response_constitution": {"direct_answer": "buy"}},
        query="Should I buy?",
    )
    assert out["playbook_validation"]["passed"] is False
