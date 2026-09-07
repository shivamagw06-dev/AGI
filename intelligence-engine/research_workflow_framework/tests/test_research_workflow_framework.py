"""Research Workflow Framework v1.0 tests."""

from __future__ import annotations

from answer_construction.response_constitution import apply_response_constitution
from institutional_playbook_framework import apply_institutional_playbook_framework
from research_workflow_framework import apply_research_workflow_framework, health, resolve_decision_objective


def test_health():
    h = health()
    assert h["status"] == "ok"
    assert h["workflow_count"] >= 6


def test_decision_objective_buy():
    obj = resolve_decision_objective("Should I buy TCS?", irl_intent="Analyse")
    assert obj["objective"] == "Evaluate Investment Opportunity"


def test_decision_objective_valuation():
    obj = resolve_decision_objective("Is Reliance expensive?", irl_intent="Valuation")
    assert obj["objective"] == "Understand Valuation"


def test_workflow_no_percentages():
    base = apply_response_constitution(
        {"executive": "TCS franchise review.", "house_label": "Constructive", "bull": ["Quality"], "bear": ["Risk"]},
        query="Should I buy TCS?",
        ticker="TCS",
        company="Tata Consultancy Services",
        confidence=65,
    )
    base = apply_institutional_playbook_framework(
        base,
        query="Should I buy TCS?",
        ticker="TCS",
        intent_resolution={"intent": "Analyse"},
    )
    out = apply_research_workflow_framework(
        base,
        query="Should I buy TCS?",
        ticker="TCS",
        company="Tata Consultancy Services",
        intent_resolution={"intent": "Analyse"},
    )
    rwf = out["research_workflow_framework"]
    assert rwf["enabled"] is True
    status = out["research_status"]
    assert status["no_percentages"] is True
    assert "progress_pct" not in status
    assert status["display"] == "Research Status"
    assert any(i["symbol"] in {"✓", "⚠", "□"} for i in status["items"])


def test_next_best_research_question_has_reason():
    out = apply_research_workflow_framework(
        {"executive": "Review", "response_constitution": {"direct_answer": "Review"}},
        query="Should I buy TCS?",
        ticker="TCS",
        company="TCS",
    )
    nbrq = out["next_best_research_question"]
    assert nbrq["question"]
    assert nbrq["reason"]
    assert "because" in nbrq["reason"].lower() or "inconclusive" in nbrq["reason"].lower() or "required" in nbrq["reason"].lower() or "institutional" in nbrq["reason"].lower() or "Relative" in nbrq["reason"] or "next" in nbrq["reason"].lower()


def test_session_persists():
    prior = {"completed_steps": ["Business Quality"], "playbooks_completed": ["Business Quality"], "turn_count": 1}
    out = apply_research_workflow_framework(
        {"executive": "Valuation", "institutional_playbook_framework": {"research_journey_state": {"completed_steps": ["Business Quality", "Valuation"]}}},
        query="Is TCS expensive?",
        ticker="TCS",
        research_session_state=prior,
    )
    session = out["research_session"]
    assert session["turn_count"] >= 2
    assert "Is TCS expensive?" in session["questions_asked"]


def test_no_forbidden_language():
    out = apply_research_workflow_framework(
        {"executive": "Strong buy with target price 5000", "response_constitution": {"direct_answer": "buy"}},
        query="Should I buy?",
    )
    assert out["workflow_validation"]["passed"] is False
