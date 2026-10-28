"""Ask Intelligence Constitution v1.0 tests."""

from __future__ import annotations

from ask_intelligence_constitution import apply_ask_intelligence_constitution, health
from ask_intelligence_constitution.intent import resolve_investment_intent
from ask_intelligence_constitution.validation import validate_ask_response
from answer_construction.response_constitution import apply_response_constitution


def test_health():
    h = health()
    assert h["status"] == "ok"
    assert h["deterministic"] is True
    assert h["llm"] is False


def test_intent_maps_buy_question():
    intent = resolve_investment_intent("Should I buy TCS?", irl_intent="Analyse")
    assert intent["primary_intent"] == "INVESTMENT_ASSESSMENT"
    assert "investment consideration" in intent["real_intent"].lower()
    assert "Business Quality" in intent["methodology"]


def test_intent_maps_valuation_question():
    intent = resolve_investment_intent("Is Reliance expensive?", irl_intent="Valuation")
    assert intent["primary_intent"] == "VALUATION"


def test_intent_maps_earnings_question():
    intent = resolve_investment_intent("Explain HDFC Bank earnings", irl_intent="Analyse")
    assert intent["primary_intent"] == "EARNINGS_ANALYSIS"


def test_apply_constitution_no_buy_sell_language():
    base = apply_response_constitution(
        {
            "executive": "TCS remains a leading IT services franchise.",
            "thesis": "Scale and client relationships support research interest.",
            "house_label": "Constructive",
            "bull": ["Client retention"],
            "bear": ["Wage inflation"],
            "institutional_answer": {"reason": "Franchise quality", "text": "Constructive research view."},
        },
        query="Should I buy TCS?",
        ticker="TCS",
        company="Tata Consultancy Services",
        confidence=72,
    )
    out = apply_ask_intelligence_constitution(
        base,
        query="Should I buy TCS?",
        intent_resolution={"intent": "Analyse"},
    )
    aic = out["ask_intelligence_constitution"]
    assert aic["enabled"] is True
    assert aic["intent"]["primary_intent"] == "INVESTMENT_ASSESSMENT"
    assert out["answer_structure"] == "ask_intelligence_constitution_v1"
    assert out["research_conclusion"]["user_decides"] is True
    assert "questions_before_you_decide" in out
    assert len(out["questions_before_you_decide"]) >= 4
    assert aic["institutional_thinking_framework"]["purpose"]


def test_validation_rejects_forbidden_language():
    pack = {
        "executive": "You must buy this stock for guaranteed returns.",
        "ask_intelligence_constitution": {
            "intent": {"primary_intent": "INVESTMENT_ASSESSMENT", "methodology": ["x"]},
            "sections": {
                "research_conclusion": {"summary": "ok"},
                "confidence": {"methodology": "test"},
            },
        },
        "research_conclusion": {"summary": "ok"},
    }
    v = validate_ask_response(pack)
    assert v["passed"] is False
    assert v["forbidden_hits"]


def test_sanitizes_buy_house_label():
    out = apply_ask_intelligence_constitution(
        {"executive": "Test", "house_label": "Buy", "response_constitution": {"direct_answer": "Test"}},
        query="Should I buy?",
    )
    assert out.get("house_label") == "Research Priority"
