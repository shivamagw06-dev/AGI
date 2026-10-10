"""AGIB Response Constitution v1.0 — soft-wire tests."""

from __future__ import annotations

from answer_construction.production import package_for_ask_agi, quality_gates
from answer_construction.response_constitution import (
    CONSTITUTION_VERSION,
    SECTION_ORDER,
    apply_response_constitution,
    explain_confidence,
    health,
)
from editorial.prompts import BASE_RULES, EDITORIAL_SYSTEM


def test_constitution_health_and_order():
    h = health()
    assert h["status"] == "ok"
    assert h["version"] == CONSTITUTION_VERSION
    assert SECTION_ORDER[0] == "direct_answer"
    assert SECTION_ORDER[-1] == "suggested_follow_ups"
    assert quality_gates()["checks"]["response_constitution_v1"] is True


def test_explain_confidence_is_prose():
    text = explain_confidence(55, reasons=["valuation remains uncertain"])
    assert "55%" in text
    assert "because" in text.lower()
    assert "valuation" in text.lower()


def test_apply_shapes_sections_without_inventing_ticker_facts():
    out = apply_response_constitution(
        {
            "enabled": True,
            "executive": "HDFC Bank remains a high-quality deposit franchise with stable loan quality.",
            "thesis": "Deposit franchise and loan quality support a constructive medium-term view.",
            "house_label": "Constructive",
            "bull": ["Stable low-cost deposits"],
            "bear": ["Net interest margin pressure if deposit costs rise"],
            "risks": ["Margin pressure"],
            "catalysts": ["Next quarterly results"],
            "why": ["Stable asset quality means fewer borrowers are failing to repay loans."],
            "institutional_answer": {
                "enabled": True,
                "recommendation": "Accumulate",
                "reason": "Deposit franchise quality remains durable versus peers.",
                "text": "HDFC Bank looks constructive on franchise quality, with margin pressure as the key watchpoint.",
            },
        },
        query="Should I buy HDFC Bank?",
        ticker="HDFCBANK",
        company="HDFC Bank",
        confidence=62,
    )
    rc = out["response_constitution"]
    assert rc["enabled"] is True
    assert rc["version"] == "1.0"
    assert rc["direct_answer"]
    assert rc["why_agib_thinks_this"]
    assert "because" in rc["why_agib_thinks_this"][0].lower()
    thesis = rc["investment_thesis"]
    for key in ("business", "growth", "financial_quality", "valuation", "risks", "catalysts"):
        assert thesis.get(key)
    assert rc["bull_vs_bear"]["bull_case"]
    assert rc["bull_vs_bear"]["bear_case"]
    assert "Bottom line" in rc["bottom_line"] or "bottom line" in rc["bottom_line"].lower()
    assert rc["confidence"]["explanation"]
    assert "because" in rc["confidence"]["explanation"].lower()
    assert out["answer_structure"] == "response_constitution_v1"
    assert out["bottom_line"]


def test_package_for_ask_agi_attaches_constitution():
    out = package_for_ask_agi(
        query="What is your view on Eternal?",
        executive="Eternal is a consumer internet platform combining food delivery and quick commerce.",
        thesis="Category leadership supports a constructive research stance pending fuller valuation evidence.",
        house_label="Constructive",
        bull=["Category leadership in food delivery"],
        bear=["Competitive cash burn risk"],
        risks=["Regulatory and competitive intensity"],
        catalysts=["Next quarterly results"],
        why=["Food delivery remains the core demand engine."],
        intelligence_construction={
            "enabled": True,
            "company_name": "Eternal",
            "executive_brief": "Eternal is a consumer internet platform combining food delivery and quick commerce.",
            "sections": {
                "financial_intelligence": {
                    "narrative": "Cash burn and unit economics decide whether growth creates value."
                },
                "valuation": {
                    "narrative": "The share price may already assume strong future growth."
                },
            },
        },
        company_analysis={
            "enabled": True,
            "identity": {
                "company_name": "Eternal",
                "business_model": "Multi-sided consumer marketplace",
            },
        },
        confidence=58,
    )
    assert out.get("response_constitution", {}).get("enabled") is True
    assert out["response_constitution"]["section_order"] == list(SECTION_ORDER)
    assert out.get("confidence_explanation")


def test_editorial_prompts_include_constitution_voice():
    assert "Response Constitution" in EDITORIAL_SYSTEM
    assert "first-time" in EDITORIAL_SYSTEM.lower() or "first stock" in EDITORIAL_SYSTEM.lower()
    assert "every opinion needs a reason" in EDITORIAL_SYSTEM.lower()
    assert "Direct Answer" in BASE_RULES
    assert "human-first institutional research" in BASE_RULES.lower()
