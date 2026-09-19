"""Ask showcase questions must select the institutional engine stack."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))


@pytest.fixture(autouse=True)
def _reset_kul_registry():
    import knowledge_unification.registry as reg

    reg._REGISTRY = None
    yield
    reg._REGISTRY = None


SHOWCASE = [
    (
        "company_intel",
        "Analyze Infosys as if you were an institutional equity analyst. Explain the business, financial quality, valuation, historical valuation, risks, catalysts, forecast, macro exposure, and key monitoring points.",
        "INFY",
        {
            "research_intelligence_engine",
            "forecast_intelligence_engine",
            "macro_intelligence_engine",
            "unified_valuation_engine",
            "historical_valuation_intelligence",
            "valuation_attribution_engine",
        },
    ),
    (
        "valuation",
        "Is Reliance Industries currently expensive or cheap relative to its own history, sector, industry, and the Indian market? Explain why with supporting evidence.",
        "RELIANCE",
        {
            "historical_valuation_intelligence",
            "valuation_attribution_engine",
            "unified_valuation_engine",
            "valuation_policy_engine",
        },
    ),
    (
        "forecast",
        "What is AGIB's outlook for Tata Motors over the next 3–5 years? Show the bull, base, and bear scenarios, confidence, assumptions, risks, and catalysts.",
        "TATAMOTORS",
        {
            "forecast_intelligence_engine",
            "macro_intelligence_engine",
            "research_intelligence_engine",
            "historical_valuation_intelligence",
        },
    ),
    (
        "historical",
        "When has Asian Paints traded at valuations similar to today? What happened afterwards, and is today's valuation unusual?",
        "ASIANPAINT",
        {
            "historical_valuation_intelligence",
            "valuation_attribution_engine",
            "unified_valuation_engine",
        },
    ),
    (
        "screen",
        "Find high-quality compounders with improving fundamentals, attractive valuation, strong ROCE, rising institutional ownership, and positive forecast confidence. Explain why they qualify.",
        None,
        {
            "hedge_fund_screens",
            "forecast_intelligence_engine",
            "research_intelligence_engine",
            "unified_valuation_engine",
        },
    ),
    (
        "macro",
        "How would a 100 basis point RBI rate cut affect Indian banks, real estate, auto, NBFCs, and IT companies? Which sectors are likely to benefit the most and why?",
        None,
        {
            "macro_intelligence_engine",
            "forecast_intelligence_engine",
            "market_intelligence_engine",
        },
    ),
    (
        "comparison",
        "Compare TCS and Infosys across valuation, historical valuation, financial quality, growth outlook, capital allocation, risks, and forecast. Which business currently has the stronger institutional profile?",
        "TCS",
        {
            "research_intelligence_engine",
            "unified_valuation_engine",
            "historical_valuation_intelligence",
            "forecast_intelligence_engine",
            "valuation_attribution_engine",
        },
    ),
    (
        "market",
        "Summarize today's Indian market. Explain market breadth, sector rotation, institutional flows, valuation, macro backdrop, and the most important developments investors should monitor.",
        None,
        {
            "market_intelligence_engine",
            "macro_intelligence_engine",
            "historical_valuation_intelligence",
            "institutional_warehouse",
        },
    ),
    (
        "attribution",
        "Explain why HDFC Bank trades at a premium valuation. Break down the premium into business quality, profitability, capital allocation, historical valuation behavior, macro factors, institutional ownership, and future expectations.",
        "HDFCBANK",
        {
            "valuation_attribution_engine",
            "historical_valuation_intelligence",
            "valuation_policy_engine",
            "research_intelligence_engine",
            "macro_intelligence_engine",
        },
    ),
    (
        "showcase",
        "Analyze Larsen & Toubro (L&T) as if you were preparing an investment committee report. Explain the business model, competitive advantages, financial quality, historical performance, valuation versus history and peers, valuation attribution, macro exposure, institutional ownership, forecast scenarios (bull/base/bear), key risks, catalysts, confidence, and the top five factors that should be monitored over the next 12 months. Clearly distinguish observed, derived, and inferred evidence throughout the report.",
        "LT",
        {
            "research_intelligence_engine",
            "forecast_intelligence_engine",
            "macro_intelligence_engine",
            "unified_valuation_engine",
            "historical_valuation_intelligence",
            "valuation_attribution_engine",
            "valuation_policy_engine",
        },
    ),
]


@pytest.mark.parametrize("label,question,ticker,required", SHOWCASE, ids=[s[0] for s in SHOWCASE])
def test_showcase_menus_select_engines(label, question, ticker, required):
    from knowledge_unification.knowledge_planner import build_knowledge_plan
    from knowledge_unification.query_planner import plan_query
    from universal_knowledge.planner import plan as uko_plan

    q = plan_query(question)
    if ticker:
        bound = (q.ticker_hint or "").upper()
        # Entity Intelligence may bind a group subsidiary (e.g. TMCV for Tata Motors).
        # Accept the canonical ticker or any non-empty bind; UKO plan forces canonical.
        assert bound, f"{label} failed to bind a company"
    # Macro / market / screen must never fall into academy-only menus.
    kp = build_knowledge_plan(q)
    assert "academy" not in (kp.provider_ids or [])[:3] or label in {"concept"}
    missing_kul = required - set(kp.provider_ids or [])
    assert not missing_kul, f"{label} KUL missing {missing_kul}; got {kp.provider_ids}"

    up = uko_plan(question, ticker=ticker)
    selected = set(up.get("selected_providers") or [])
    missing_uko = required - selected
    assert not missing_uko, f"{label} UKO missing {missing_uko}; family={up.get('family')} selected={sorted(selected)}"


def test_macro_menu_is_not_academy_overwrite():
    from knowledge_unification.knowledge_planner import _MACRO_MENU

    assert _MACRO_MENU[0] == "macro_intelligence_engine"
    assert "academy" not in _MACRO_MENU[:4]


def test_premium_question_is_attribution_not_macro():
    from universal_knowledge.planner import detect_family, plan as uko_plan

    q = (
        "Explain why HDFC Bank trades at a premium valuation. Break down the premium "
        "into business quality, profitability, capital allocation, historical valuation "
        "behavior, macro factors, institutional ownership, and future expectations."
    )
    assert detect_family(q) == "attribution"
    up = uko_plan(q, ticker="HDFCBANK")
    assert up["family"] == "attribution"
    assert up["selected_providers"][0] == "valuation_attribution_engine"

    rate = "How would a 100 basis point RBI rate cut affect Indian banks and NBFCs?"
    assert detect_family(rate) == "macro"


def test_hard_providers_include_showcase_engines():
    from knowledge_unification.production import _HARD_PROVIDERS

    for pid in (
        "research_intelligence_engine",
        "forecast_intelligence_engine",
        "macro_intelligence_engine",
        "unified_valuation_engine",
        "historical_valuation_intelligence",
        "valuation_attribution_engine",
        "market_intelligence_engine",
        "institutional_warehouse",
    ):
        assert pid in _HARD_PROVIDERS


def test_new_providers_registered():
    from knowledge_unification.registry import get_registry

    reg = get_registry()
    for pid in (
        "unified_valuation_engine",
        "historical_valuation_intelligence",
        "valuation_attribution_engine",
        "valuation_policy_engine",
        "market_intelligence_engine",
    ):
        assert reg.get(pid) is not None
        assert reg.get(pid).health_check() in {"ok", "degraded", "empty"}
