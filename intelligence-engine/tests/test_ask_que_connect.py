"""Ask ↔ QUE connection — research brief on short-circuits; investment decisions escalate."""

from __future__ import annotations

from app.ui.service import (
    _build_que_answer_construction,
    _kul_is_deterministic_business_answer,
    _que_requires_full_desk,
    UiService,
)


def test_que_pack_research_priority():
    pack = _build_que_answer_construction(
        "Does Tata Consultancy Services deserve research today?",
        ticker="TCS",
        company="Tata Consultancy Services",
    )
    assert pack["enabled"] is True
    assert pack["decision_type"] == "Research Priority"
    assert pack["research_brief"]["decision_type"] == "Research Priority"
    assert pack["primary_investment_question"]
    assert len(pack["top_research_questions"]) == 3
    assert _que_requires_full_desk(pack) is True


def test_que_pack_capital_allocation():
    pack = _build_que_answer_construction("Should I buy TCS?", ticker="TCS")
    assert pack["decision_type"] == "Capital Allocation"
    assert _que_requires_full_desk(pack) is True


def test_investment_view_and_corporate_event_require_full_research_desk():
    from institutional_output_quality.guards import requires_full_company_analysis

    questions = (
        "What is AGI's view on Zen Technologies' ₹295 crore defence order?",
        "What is your investment thesis on TCS?",
        "What would change your view on Infosys?",
        "How material is Reliance's new contract to the investment case?",
        "Assess the investment impact of Zen Technologies' 295 crore defence order",
    )
    for question in questions:
        pack = _build_que_answer_construction(question, ticker="ZENTEC")
        assert pack["decision_type"] == "Thesis Validation"
        assert _que_requires_full_desk(pack) is True
        assert requires_full_company_analysis(question, "ZENTEC") is True


def test_education_does_not_require_full_desk():
    pack = _build_que_answer_construction("Explain free cash flow in plain English for a new investor")
    # Education / concept teaching can stay on KUL / financial router.
    assert pack["decision_type"] == "Education"
    assert _que_requires_full_desk(pack) is False


def test_deterministic_business_answer_is_not_discarded_by_que():
    hit = {
        "providers_used": ["business_intelligence", "industry_intelligence"],
        "company_intelligence": {"identity": {"ticker": "AAPL"}},
    }
    assert _kul_is_deterministic_business_answer(
        "Why is Apple able to sustain premium pricing?", hit
    ) is True


def test_management_quality_keeps_bi_and_skips_full_desk():
    from institutional_output_quality.guards import (
        is_scoped_business_axis_question,
        requires_full_company_analysis,
    )

    q = "Evaluate management quality for Reliance Industries."
    assert is_scoped_business_axis_question(q) is True
    assert requires_full_company_analysis(q, "RELIANCE") is False
    hit = {
        "providers_used": ["business_intelligence", "investment_intelligence"],
        "company_intelligence": {"identity": {"ticker": "RELIANCE"}},
    }
    assert _kul_is_deterministic_business_answer(q, hit) is True
    # Broad evaluate without a BI axis still escalates.
    assert requires_full_company_analysis("Evaluate Reliance Industries.", "RELIANCE") is True


def test_recommendation_policy_attaches_research_brief():
    svc = UiService.__new__(UiService)
    from app.ui.ask_orchestration_trace import StageTimer

    view = svc._recommendation_policy_view(
        question="Should I buy TCS?",
        ticker="TCS",
        ask_trace_id="test-que-reco",
        stage_timer=StageTimer(ask_trace_id="test-que-reco"),
        ask_orchestration={"ask_trace_id": "test-que-reco"},
        entity_resolution={},
        ere_body={},
        alias_hit="TCS",
        que_pack=_build_que_answer_construction("Should I buy TCS?", ticker="TCS"),
    )
    assert view.answer_policy == "no_buy_sell_recommendation"
    assert view.answer_construction.get("enabled") is True
    assert view.answer_construction.get("decision_type") == "Capital Allocation"
    assert view.answer.get("research_brief")
    assert "capital allocation" in (view.executive_summary or "").lower()
    assert view.follow_up_questions
    assert "question_understanding_engine" in view.meta.sources
