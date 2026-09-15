"""IFAC — institutional composition above engines; consensus never headlines."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))


def _pack(pid, summary, *, why=None, confidence=0.8, empty=False):
    return {
        "provider_id": pid,
        "ok": True,
        "empty": empty,
        "confidence": confidence,
        "summary": summary,
        "why": why or [f"{pid} evidence"],
        "evidence": [{"explainability": {"observed": [f"{pid} observed"], "derived": [], "inferred": []}}],
        "facts": [],
        "raw": {},
    }


def test_company_template_demotes_consensus_headline():
    from intelligence_fusion_answer_composer.compose import compose

    out = compose(
        question="Analyze Infosys as if you were an institutional equity analyst.",
        family="company_intel",
        ticker="INFY",
        provider_results=[
            _pack(
                "valuation_consensus",
                "Infosys Limited — Capital IQ market consensus: consensus target 1,039.75, 42 analysts covering.",
                confidence=0.9,
            ),
            _pack(
                "research_intelligence_engine",
                "Infosys is an IT services franchise with durable client relationships and high free-cash conversion.",
                why=["Recurring revenue mix supports quality.", "Key monitor: deal wins and attrition."],
            ),
            _pack(
                "forecast_intelligence_engine",
                "Base case: mid-single-digit revenue growth with stable margins over 3–5 years.",
            ),
            _pack(
                "unified_valuation_engine",
                "Primary metric PE; current multiple sits near sector norms under VPAE.",
            ),
        ],
        fused={
            "summary": "Infosys Limited — Capital IQ market consensus: consensus target 1,039.75, 42 analysts covering."
        },
    )
    assert out["ok"] is True
    assert out["template"] == "company"
    assert out["primary_engine"] == "research_intelligence_engine"
    assert "Capital IQ market consensus" not in out["summary"]
    assert "IT services franchise" in out["summary"]
    assert out["consensus_demoted"] is True
    titles = [s["title"] for s in out["sections"]]
    assert "Executive Summary" in titles
    assert "External Consensus" in titles
    # Consensus section exists but is near the end.
    assert titles.index("External Consensus") > titles.index("Current Valuation")


def test_macro_family_prefers_mie_not_company_engines():
    from intelligence_fusion_answer_composer.compose import compose

    out = compose(
        question="How would a 100 basis point RBI rate cut affect Indian banks and NBFCs?",
        family="macro",
        provider_results=[
            _pack("business_intelligence", "For infrastructure, enterprise value is primarily driven by Order Book."),
            _pack(
                "macro_intelligence_engine",
                "A 100bp rate cut eases funding costs for banks and NBFCs; rate-sensitive sectors benefit first.",
            ),
            _pack("market_intelligence_engine", "Financials lead sector rotation when policy eases."),
        ],
    )
    assert out["primary_engine"] == "macro_intelligence_engine"
    assert "rate cut" in out["summary"].lower() or "funding" in out["summary"].lower()
    assert "Order Book" not in out["summary"]


def test_missing_history_uses_institutional_explanation():
    from intelligence_fusion_answer_composer.compose import compose

    out = compose(
        question="When has Asian Paints traded at valuations similar to today?",
        family="historical",
        ticker="ASIANPAINT",
        provider_results=[
            _pack(
                "historical_valuation_intelligence",
                "AGIB holds no historical price-to-earnings observations for ASIANPAINT, so no historical conclusion can be drawn.",
            ),
            _pack(
                "unified_valuation_engine",
                "Asian Paints trades at 55x PE versus a specialty chemicals peer median near 31x.",
            ),
        ],
    )
    assert out["ok"] is True
    hist = next(s for s in out["sections"] if s["id"] == "historical_valuation")
    body = (hist.get("body") or hist.get("missing") or "").lower()
    assert "no historical conclusion" not in body
    assert "observation threshold" in body or "unavailable" in body


def test_screen_family_leads_with_hedge_fund_lab():
    from intelligence_fusion_answer_composer.compose import compose

    out = compose(
        question="Find high-quality compounders with attractive valuation.",
        family="screen",
        provider_results=[
            _pack(
                "hedge_fund_screens",
                "Hedge Fund Lab Quality screen — 12 research observations from 1184 companies.",
            ),
            _pack("valuation_consensus", "Random consensus noise should not lead."),
        ],
    )
    assert out["primary_engine"] == "hedge_fund_screens"
    assert out["summary"].startswith("Hedge Fund Lab")


def test_health_and_routing_surface():
    from intelligence_fusion_answer_composer import health, routing_table, templates_catalog

    h = health()
    assert h["ok"] is True
    assert h["generates_intelligence"] is False
    assert "compose" in str(h["endpoints"])
    assert routing_table()["ok"] is True
    assert "company" in templates_catalog()["templates"]


def test_string_provider_results_do_not_crash():
    from intelligence_fusion_answer_composer.compose import compose

    out = compose(
        question="Compare TCS and Infosys across valuation and forecast.",
        family="comparison",
        provider_results=[
            "unexpected string result",
            _pack("research_intelligence_engine", "TCS and Infosys are peer IT services platforms; compare quality and valuation side by side."),
            _pack("unified_valuation_engine", "Both screen on PE; relative premium depends on growth durability."),
        ],
    )
    assert out["ok"] is True
    assert out["primary_engine"] == "research_intelligence_engine"


def test_attribution_overrides_misclassified_macro_family():
    from intelligence_fusion_answer_composer.compose import compose
    from intelligence_fusion_answer_composer.priorities import resolve_family
    from universal_knowledge.planner import detect_family

    q = (
        "Why does HDFC Bank trade at a premium to peers? Break down the premium. "
        "Include valuation attribution, peer context, and macro factors."
    )
    assert detect_family(q) == "attribution"
    assert resolve_family("macro", q) == "attribution"

    out = compose(
        question=q,
        family="macro",  # intentional misclassification from older planner
        ticker="HDFCBANK",
        provider_results=[
            _pack(
                "macro_intelligence_engine",
                "Rate conditions affect bank NIMs; this must not headline a premium question.",
            ),
            _pack(
                "valuation_attribution_engine",
                "HDFC Bank's premium is explained by deposit franchise quality, ROA durability, and lower credit cost versus peers.",
            ),
            _pack(
                "valuation_consensus",
                "HDFC Bank — Capital IQ market consensus: consensus target 1,800, 45 analysts covering.",
            ),
        ],
    )
    assert out["family"] == "attribution"
    assert out["template"] == "attribution"
    assert out["primary_engine"] == "valuation_attribution_engine"
    assert "Capital IQ" not in out["summary"]
    assert "deposit franchise" in out["summary"].lower() or "premium" in out["summary"].lower()


def test_company_lead_skips_fie_risk_dump_for_business_intelligence():
    from intelligence_fusion_answer_composer.compose import compose

    out = compose(
        question="Analyze Infosys as if you were an institutional equity analyst.",
        family="company_intel",
        ticker="INFY",
        provider_results=[
            _pack(
                "forecast_intelligence_engine",
                "{'risk_register': ['attrition', 'pricing'], 'key_risks': 'monitor deal wins'}",
            ),
            _pack(
                "business_intelligence",
                "Infosys is a scaled IT services platform with durable client relationships and high cash conversion.",
            ),
            _pack(
                "valuation_consensus",
                "Infosys Limited — Capital IQ market consensus: consensus target 1,039.75.",
            ),
        ],
    )
    assert out["primary_engine"] == "business_intelligence"
    assert "risk_register" not in out["summary"]
    assert "IT services" in out["summary"]
